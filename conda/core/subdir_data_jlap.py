"""
Code to handle incremental repodata updates.

Replaces subdir_data.fetch_repodata_remote_request
"""

import contextlib
import hashlib
import json
import logging
import os
import warnings
from pathlib import Path
from ..models.channel import Channel, all_channel_urls
from os.path import dirname

from ..auxlib.logz import stringify
from ..base.constants import CONDA_HOMEPAGE_URL, CONDA_PACKAGE_EXTENSION_V1, REPODATA_FN
from ..base.context import context
from ..common.url import join_url, maybe_unquote
from ..exceptions import (
    CondaDependencyError,
    CondaHTTPError,
    CondaSSLError,
    CondaUpgradeError,
    NotWritableError,
    ProxyError,
    UnavailableInvalidChannel,
)
from ..gateways.connection import (
    ConnectionError,
    HTTPError,
    InsecureRequestWarning,
    InvalidSchema,
    RequestsProxyError,
    SSLError,
)
from ..gateways.connection.session import CondaSession
from .subdir_data import Response304ContentUnchanged

log = logging.getLogger(__name__)
stderrlog = logging.getLogger("conda.stderrlog")


def fetch_repodata_remote_request(
    url: str, state_fn: str | os.PathLike, repodata_fn: str | os.PathLike
):
    """
    state_fn: a json sidecar file with the state.
    """
    if not context.ssl_verify:
        warnings.simplefilter("ignore", InsecureRequestWarning)

    state_fn = Path(state_fn)
    repodata_fn = Path(repodata_fn)

    try:
        state = json.loads(Path(state_fn).read_text())
    except Exception as e:
        log.exception("Error loading state for %s", url)
        state = {}

    etag = state.get("etag")
    mod_stamp = state.get("lmod")

    session = CondaSession()

    headers = {}
    if etag:
        headers["If-None-Match"] = etag
    if mod_stamp:
        headers["If-Modified-Since"] = mod_stamp

    headers["Accept-Encoding"] = "gzip, deflate, compress, identity"
    headers["Accept"] = "application/json"
    filename = repodata_fn

    with conda_http_errors(str(url), str(repodata_fn)):
        timeout = context.remote_connect_timeout_secs, context.remote_read_timeout_secs
        resp = session.get(
            join_url(url, filename), headers=headers, proxies=session.proxies, timeout=timeout
        )
        if log.isEnabledFor(logging.DEBUG):
            log.debug(stringify(resp, content_max_len=256))
        resp.raise_for_status()

    if resp.status_code == 304:
        raise Response304ContentUnchanged()

    json_str = resp.content

    saved_fields = {"_url": url}
    # XXX store in state
    add_http_value_to_dict(resp, "Etag", saved_fields, "_etag")
    add_http_value_to_dict(resp, "Last-Modified", saved_fields, "_mod")
    add_http_value_to_dict(resp, "Cache-Control", saved_fields, "_cache_control")

    # DON'T add extra values to the raw repodata json
    # state_fn.

    return json_str


def add_http_value_to_dict(resp, http_key, d, dict_key):
    value = resp.headers.get(http_key)
    if value:
        d[dict_key] = value


@contextlib.contextmanager
def conda_http_errors(url, repodata_fn):
    try:
        yield
    except RequestsProxyError:
        raise ProxyError()  # see #3962

    except InvalidSchema as e:
        if "SOCKS" in str(e):
            message = """\
Requests has identified that your current working environment is configured
to use a SOCKS proxy, but pysocks is not installed.  To proceed, remove your
proxy configuration, run `conda install pysocks`, and then you can re-enable
your proxy configuration.
"""
            raise CondaDependencyError(message)
        else:
            raise

    except SSLError as e:
        # SSLError: either an invalid certificate or OpenSSL is unavailable
        try:
            import ssl  # noqa: F401
        except ImportError:
            raise CondaSSLError(
                f"""\
OpenSSL appears to be unavailable on this machine. OpenSSL is required to
download and install packages.

Exception: {e}
"""
            )
        else:
            raise CondaSSLError(
                f"""\
Encountered an SSL error. Most likely a certificate verification issue.

Exception: {e}
"""
            )

    except (ConnectionError, HTTPError) as e:
        status_code = getattr(e.response, "status_code", None)
        if status_code in (403, 404):
            if not url.endswith("/noarch"):
                log.info(
                    "Unable to retrieve repodata (response: %d) for %s",
                    status_code,
                    url + "/" + repodata_fn,
                )
                return None
            else:
                if context.allow_non_channel_urls:
                    stderrlog.warning(
                        "Unable to retrieve repodata (response: %d) for %s",
                        status_code,
                        url + "/" + repodata_fn,
                    )
                    return None
                else:
                    raise UnavailableInvalidChannel(
                        Channel(dirname(url)),
                        status_code,
                        response=e.response,
                    )

        elif status_code == 401:
            channel = Channel(url)
            if channel.token:
                help_message = """\
The token '%s' given for the URL is invalid.

If this token was pulled from anaconda-client, you will need to use
anaconda-client to reauthenticate.

If you supplied this token to conda directly, you will need to adjust your
conda configuration to proceed.

Use `conda config --show` to view your configuration's current state.
Further configuration help can be found at <%s>.
""" % (
                    channel.token,
                    join_url(CONDA_HOMEPAGE_URL, "docs/config.html"),
                )

            elif context.channel_alias.location in url:
                # Note, this will not trigger if the binstar configured url does
                # not match the conda configured one.
                help_message = """\
The remote server has indicated you are using invalid credentials for this channel.

If the remote site is anaconda.org or follows the Anaconda Server API, you
will need to
    (a) remove the invalid token from your system with `anaconda logout`, optionally
        followed by collecting a new token with `anaconda login`, or
    (b) provide conda with a valid token directly.

Further configuration help can be found at <%s>.
""" % join_url(
                    CONDA_HOMEPAGE_URL, "docs/config.html"
                )

            else:
                help_message = """\
The credentials you have provided for this URL are invalid.

You will need to modify your conda configuration to proceed.
Use `conda config --show` to view your configuration's current state.
Further configuration help can be found at <%s>.
""" % join_url(
                    CONDA_HOMEPAGE_URL, "docs/config.html"
                )

        elif status_code is not None and 500 <= status_code < 600:
            help_message = """\
A remote server error occurred when trying to retrieve this URL.

A 500-type error (e.g. 500, 501, 502, 503, etc.) indicates the server failed to
fulfill a valid request.  The problem may be spurious, and will resolve itself if you
try your request again.  If the problem persists, consider notifying the maintainer
of the remote server.
"""

        else:
            if url.startswith("https://repo.anaconda.com/"):
                help_message = """\
An HTTP error occurred when trying to retrieve this URL.
HTTP errors are often intermittent, and a simple retry will get you on your way.

If your current network has https://www.anaconda.com blocked, please file
a support request with your network engineering team.

%s
""" % maybe_unquote(
                    repr(url)
                )

            else:
                help_message = """\
An HTTP error occurred when trying to retrieve this URL.
HTTP errors are often intermittent, and a simple retry will get you on your way.
%s
""" % maybe_unquote(
                    repr(url)
                )

        raise CondaHTTPError(
            help_message,
            join_url(url, repodata_fn),
            status_code,
            getattr(e.response, "reason", None),
            getattr(e.response, "elapsed", None),
            e.response,
            caused_by=e,
        )
