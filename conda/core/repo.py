import abc
import bz2
import json
import logging
import os
import warnings

from typing import List, Dict, Optional, TypedDict

from conda.auxlib.ish import dals
from conda.auxlib.logz import stringify

from conda.base.context import context
from conda.base.constants import CONDA_HOMEPAGE_URL, REPODATA_FN
from conda.common.compat import ensure_text_type
from conda.common.url import join_url, maybe_unquote
from conda.exceptions import (
    CondaDependencyError,
    CondaHTTPError,
    CondaSSLError,
    UnavailableInvalidChannel,
    ProxyError,
)
from conda.gateways.connection import (
    ConnectionError,
    HTTPError,
    InsecureRequestWarning,
    InvalidSchema,
    SSLError,
    RequestsProxyError,
)
from conda.gateways.connection.session import CondaSession
from conda.models.channel import Channel


Repodata = TypedDict('Repodata', {  # TODO: Use more specific types
    'info': TypedDict('RepodataInfo', {
        'subdir': str,
    }),
    'packages': Dict[
        str,  # filename
        TypedDict('RepodataPackage', {
            'build': str,
            'build_number': int,
            'depends': List[str],
            'license': str,
            'md5': str,
            'name': str,
            'sha256': str,
            'size': int,
            'subdir': str,
            'timestamp': int,
            'version': str,
        }),
    ],
})


class RepoInterface(abc.ABC):
    # TODO: Support async operations
    # TODO: Support progress bars
    def repodata(self, etag: Optional[str], last_modified: Optional[str]) -> Repodata: ...


class Response304ContentUnchanged(Exception):
    pass


class CondaRepoInterface(RepoInterface):
    def __init__(self, url: str, repodata_fn: Optional[str]) -> None:
        self._url = url
        self._repodata_fn = repodata_fn

        self._log = logging.getLogger(__name__)
        self._stderrlog = logging.getLogger('conda.stderrlog')

    def repodata(self, etag: Optional[str], last_modified: Optional[str]) -> Repodata:
        if not context.ssl_verify:
            warnings.simplefilter('ignore', InsecureRequestWarning)

        session = CondaSession()

        headers = {}
        if etag:
            headers['If-None-Match'] = etag
        if last_modified:
            headers['If-Modified-Since'] = last_modified
        filename = self._repodata_fn

        try:
            timeout = context.remote_connect_timeout_secs, context.remote_read_timeout_secs
            resp = session.get(join_url(self._url, filename), headers=headers, proxies=session.proxies,
                            timeout=timeout)
            if self._log.isEnabledFor(logging.DEBUG):
                self._log.debug(stringify(resp, content_max_len=256))
            resp.raise_for_status()

        except RequestsProxyError:
            raise ProxyError()   # see #3962

        except InvalidSchema as e:
            if 'SOCKS' in str(e):
                message = dals("""
                Requests has identified that your current working environment is configured
                to use a SOCKS proxy, but pysocks is not installed.  To proceed, remove your
                proxy configuration, run `conda install pysocks`, and then you can re-enable
                your proxy configuration.
                """)
                raise CondaDependencyError(message)
            else:
                raise

        except SSLError as e:
            # SSLError: either an invalid certificate or OpenSSL is unavailable
            try:
                import ssl  # noqa: F401
            except ImportError:
                raise CondaSSLError(
                    dals(
                        f"""
                        OpenSSL appears to be unavailable on this machine. OpenSSL is required to
                        download and install packages.

                        Exception: {e}
                        """
                    )
                )
            else:
                raise CondaSSLError(
                    dals(
                        f"""
                        Encountered an SSL error. Most likely a certificate verification issue.

                        Exception: {e}
                        """
                    )
                )

        except (ConnectionError, HTTPError) as e:
            status_code = getattr(e.response, 'status_code', None)
            if status_code in (403, 404):
                if not self._url.endswith('/noarch'):
                    self._log.info("Unable to retrieve repodata (response: %d) for %s", status_code,
                            self._url + '/' + self._repodata_fn)
                elif context.allow_non_channel_urls:
                    self._stderrlog.warning("Unable to retrieve repodata (response: %d) for %s",
                                    status_code, self._url + '/' + self._repodata_fn)

                # could not read the specified repodata file, fallback to old one
                if self._repodata_fn != REPODATA_FN:
                    self._repodata_fn = REPODATA_FN
                    return self.repodata(etag, last_modified)

                raise UnavailableInvalidChannel(
                    Channel(os.path.dirname(self._url)),
                    status_code,
                    response=e.response,
                )

            elif status_code == 401:
                channel = Channel(self._url)
                if channel.token:
                    help_message = dals("""
                    The token '%s' given for the URL is invalid.

                    If this token was pulled from anaconda-client, you will need to use
                    anaconda-client to reauthenticate.

                    If you supplied this token to conda directly, you will need to adjust your
                    conda configuration to proceed.

                    Use `conda config --show` to view your configuration's current state.
                    Further configuration help can be found at <%s>.
                """) % (channel.token, join_url(CONDA_HOMEPAGE_URL, 'docs/config.html'))

                elif context.channel_alias.location in self._url:
                    # Note, this will not trigger if the binstar configured url does
                    # not match the conda configured one.
                    help_message = dals("""
                    The remote server has indicated you are using invalid credentials for this channel.

                    If the remote site is anaconda.org or follows the Anaconda Server API, you
                    will need to
                    (a) remove the invalid token from your system with `anaconda logout`, optionally
                        followed by collecting a new token with `anaconda login`, or
                    (b) provide conda with a valid token directly.

                    Further configuration help can be found at <%s>.
                """) % join_url(CONDA_HOMEPAGE_URL, 'docs/config.html')

                else:
                    help_message = dals("""
                    The credentials you have provided for this URL are invalid.

                    You will need to modify your conda configuration to proceed.
                    Use `conda config --show` to view your configuration's current state.
                    Further configuration help can be found at <%s>.
                    """) % join_url(CONDA_HOMEPAGE_URL, 'docs/config.html')

            elif status_code is not None and 500 <= status_code < 600:
                help_message = dals("""
                A remote server error occurred when trying to retrieve this URL.

                A 500-type error (e.g. 500, 501, 502, 503, etc.) indicates the server failed to
                fulfill a valid request.  The problem may be spurious, and will resolve itself if you
                try your request again.  If the problem persists, consider notifying the maintainer
                of the remote server.
                """)

            else:
                if self._url.startswith("https://repo.anaconda.com/"):
                    help_message = dals("""
                    An HTTP error occurred when trying to retrieve this URL.
                    HTTP errors are often intermittent, and a simple retry will get you on your way.

                    If your current network has https://www.anaconda.com blocked, please file
                    a support request with your network engineering team.

                    %s
                    """) % maybe_unquote(repr(self._url))
                else:
                    help_message = dals("""
                    An HTTP error occurred when trying to retrieve this URL.
                    HTTP errors are often intermittent, and a simple retry will get you on your way.
                    %s
                    """) % maybe_unquote(repr(self._url))

            raise CondaHTTPError(help_message,
                                join_url(self._url, filename),
                                status_code,
                                getattr(e.response, 'reason', None),
                                getattr(e.response, 'elapsed', None),
                                e.response,
                                caused_by=e)

        if resp.status_code == 304:
            raise Response304ContentUnchanged()

        def maybe_decompress(filename, resp_content):
            return ensure_text_type(bz2.decompress(resp_content)
                                    if filename.endswith('.bz2')
                                    else resp_content).strip()

        json_str = maybe_decompress(filename, resp.content)

        saved_fields = {'_url': self._url}
        self._add_http_value_to_dict(resp, 'Etag', saved_fields, '_etag')
        self._add_http_value_to_dict(resp, 'Last-Modified', saved_fields, '_mod')
        self._add_http_value_to_dict(resp, 'Cache-Control', saved_fields, '_cache_control')

        # add extra values to the raw repodata json
        if json_str and json_str != "{}":
            return {**saved_fields, **json.loads(json_str)}

        return saved_fields

    def _add_http_value_to_dict(self, resp, http_key, d, dict_key):
        value = resp.headers.get(http_key)
        if value:
            d[dict_key] = value

