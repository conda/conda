# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import abc
import json
import logging
import pathlib
import warnings
from contextlib import contextmanager
from os.path import dirname

from conda.auxlib.logz import stringify
from conda.base.constants import CONDA_HOMEPAGE_URL, REPODATA_FN
from conda.base.context import context
from conda.common.url import join_url, maybe_unquote
from conda.exceptions import (
    CondaDependencyError,
    CondaHTTPError,
    CondaSSLError,
    ProxyError,
    UnavailableInvalidChannel,
)
from conda.gateways.connection import (
    ConnectionError,
    HTTPError,
    InsecureRequestWarning,
    InvalidSchema,
    RequestsProxyError,
    Response,
    SSLError,
)
from conda.gateways.connection.session import CondaSession
from conda.models.channel import Channel

log = logging.getLogger(__name__)
stderrlog = logging.getLogger("conda.stderrlog")


class RepodataIsEmpty(UnavailableInvalidChannel):
    """
    Subclass used to determine when empty repodata should be cached, e.g. for a
    channel that doesn't provide current_repodata.json
    """


class RepoInterface(abc.ABC):
    # TODO: Support async operations
    # TODO: Support progress bars
    def repodata(self, state: dict) -> str:
        """
        Given a mutable state dictionary with information about the cache,
        return repodata.json (or current_repodata.json) as a str. This function
        also updates state, which is expected to be saved by the caller.
        """
        ...


class Response304ContentUnchanged(Exception):
    pass


class CondaRepoInterface(RepoInterface):
    """
    Provides an interface for retrieving repodata data from channels
    """

    #: Channel URL
    _url: str

    #: Filename of the repodata file; defaults to value of conda.base.constants.REPODATA_FN
    _repodata_fn: str

    def __init__(self, url: str, repodata_fn: str | None, **kwargs) -> None:
        self._url = url
        self._repodata_fn = repodata_fn or REPODATA_FN

    def repodata(self, state: RepodataState) -> str | None:
        if not context.ssl_verify:
            warnings.simplefilter("ignore", InsecureRequestWarning)

        session = CondaSession()

        headers = {}
        etag = state.etag
        last_modified = state.mod
        if etag:
            headers["If-None-Match"] = str(etag)
        if last_modified:
            headers["If-Modified-Since"] = str(last_modified)
        filename = self._repodata_fn

        url = join_url(self._url, filename)

        with conda_http_errors(self._url, filename):
            timeout = context.remote_connect_timeout_secs, context.remote_read_timeout_secs
            response: Response = session.get(
                url, headers=headers, proxies=session.proxies, timeout=timeout
            )
            if log.isEnabledFor(logging.DEBUG):
                log.debug(stringify(response, content_max_len=256))
            response.raise_for_status()

        if response.status_code == 304:
            # should we save cache-control to state here to put another n
            # seconds on the "make a remote request" clock and/or touch cache
            # mtime
            raise Response304ContentUnchanged()

        json_str = response.text

        # We no longer add these tags to the large `resp.content` json
        saved_fields = {"_url": self._url}
        _add_http_value_to_dict(response, "Etag", saved_fields, "_etag")
        _add_http_value_to_dict(response, "Last-Modified", saved_fields, "_mod")
        _add_http_value_to_dict(response, "Cache-Control", saved_fields, "_cache_control")

        state.clear()
        state.update(saved_fields)

        return json_str


def _add_http_value_to_dict(resp, http_key, d, dict_key):
    value = resp.headers.get(http_key)
    if value:
        d[dict_key] = value


@contextmanager
def conda_http_errors(url, repodata_fn):
    """
    Use in a with: statement to translate requests exceptions to conda ones.
    """
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
                raise RepodataIsEmpty(
                    Channel(dirname(url)),
                    status_code,
                    response=e.response,
                )
            else:
                if context.allow_non_channel_urls:
                    stderrlog.warning(
                        "Unable to retrieve repodata (response: %d) for %s",
                        status_code,
                        url + "/" + repodata_fn,
                    )
                    raise RepodataIsEmpty(
                        Channel(dirname(url)),
                        status_code,
                        response=e.response,
                    )
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
The token '{}' given for the URL is invalid.

If this token was pulled from anaconda-client, you will need to use
anaconda-client to reauthenticate.

If you supplied this token to conda directly, you will need to adjust your
conda configuration to proceed.

Use `conda config --show` to view your configuration's current state.
Further configuration help can be found at <{}>.
""".format(
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


class RepodataState(dict):
    """
    Load/save `.state.json` that accompanies cached `repodata.json`
    """

    def __init__(self, cache_path_json, cache_path_state, repodata_fn):
        self.cache_path_json = pathlib.Path(cache_path_json)
        self.cache_path_state = pathlib.Path(cache_path_state)
        self.repodata_fn = repodata_fn

    def load(self):
        """
        Cache headers and additional data needed to keep track of the cache are
        stored separately, instead of the previous "added to repodata.json"
        arrangement.
        """
        try:
            state_path = self.cache_path_state
            log.debug("Load %s cache from %s", self.repodata_fn, state_path)
            state = json.loads(state_path.read_text())
            # json and state files should match
            json_stat = self.cache_path_json.stat()
            if not (
                state.get("mtime_ns") == json_stat.st_mtime_ns
                and state.get("size") == json_stat.st_size
            ):
                # clear mod, etag, cache_control to encourage re-download
                state.update({"etag": "", "mod": "", "cache_control": "", "size": 0})
            for field in (
                "etag",
                "mod",
                "cache_control",
                "size",
            ):
                alias = field
                if alias in state:
                    self[field] = state[alias]
        except (json.JSONDecodeError, OSError):
            log.debug("Could not load state", exc_info=True)
            self.clear()
        return self

    def save(self):
        """
        Must be called after writing cache_path_json, as its mtime is included in .state.json
        """
        json_stat = self.cache_path_json.stat()
        serialized = {"mtime_ns": json_stat.st_mtime_ns, "size": json_stat.st_size}
        for field in (
            "etag",
            "mod",
            "cache_control",
            "size",
        ):
            alias = field
            if field in self:
                serialized[alias] = self[field]
        return pathlib.Path(self.cache_path_state).write_text(json.dumps(serialized, indent=True))

    @property
    def mod(self) -> str:
        """
        Last-Modified header or ""
        """
        return self.get("mod", "")

    @mod.setter
    def mod(self, value):
        self["mod"] = value or ""

    @property
    def etag(self) -> str:
        """
        Etag header or ""
        """
        return self.get("etag", "")

    @etag.setter
    def etag(self, value):
        self["etag"] = value or ""

    @property
    def cache_control(self) -> str:
        """
        Cache-Control header or ""
        """
        return self.get("cache_control", "")

    @cache_control.setter
    def cache_control(self, value):
        self["cache_control"] = value or ""
