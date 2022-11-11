"""
Code to handle incremental repodata updates as described in CEP 10.
"""

from __future__ import annotations

import logging
import warnings
from pathlib import Path

from ...auxlib.logz import stringify
from ...base.context import context
from ..connection import (
    InsecureRequestWarning,
)
from ..connection.session import CondaSession
from . import RepoInterface, Response304ContentUnchanged, conda_http_errors

log = logging.getLogger(__name__)
stderrlog = logging.getLogger("conda.stderrlog")

from . import jlapper


class JlapRepoInterface(RepoInterface):
    def __init__(self, url: str, repodata_fn: str | Path, cache_path_json: str | Path, cache_path_state: str | Path, **kwargs) -> None:
        self._url = url
        self._repodata_fn = Path(repodata_fn)

        self.cache_path_json = cache_path_json
        self.cache_path_state = cache_path_state

        self._log = logging.getLogger(__name__)
        self._stderrlog = logging.getLogger("conda.stderrlog")

    def repodata(self, state: dict) -> str | None:
        """
        Fetch repodata, using adjacent .jlap file for deltas if available.
        """
        if not context.ssl_verify:
            warnings.simplefilter("ignore", InsecureRequestWarning)

        url = self._url
        repodata_fn = self._repodata_fn

        etag = state.get("_etag")
        mod_stamp = state.get("_mod")

        session = CondaSession()

        with conda_http_errors(str(url), str(repodata_fn)):
            timeout = context.remote_connect_timeout_secs, context.remote_read_timeout_secs
            resp = jlapper.request_url_jlap(url)
            if log.isEnabledFor(logging.DEBUG):
                log.debug(stringify(resp, content_max_len=256))

        if resp.status_code == 304:
            raise Response304ContentUnchanged()

        json_str = resp.content

        saved_fields = {}
        _add_http_value_to_dict(resp, "Etag", saved_fields, "_etag")
        _add_http_value_to_dict(resp, "Last-Modified", saved_fields, "_mod")
        _add_http_value_to_dict(resp, "Cache-Control", saved_fields, "_cache_control")

        state.update(saved_fields)

        return json_str


def _add_http_value_to_dict(resp, http_key, d, dict_key):
    value = resp.headers.get(http_key)
    if value:
        d[dict_key] = value
