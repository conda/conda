import logging
import warnings
from typing import Optional

from conda.auxlib.logz import stringify
from conda.base.context import context
from conda.common.compat import ensure_text_type
from conda.common.url import join_url
from conda.gateways.connection import (
    InsecureRequestWarning,
)
from conda.gateways.connection.session import CondaSession
from conda.models.channel import Channel

from . import jlapper
from .repo import RepoInterface, Response304ContentUnchanged, conda_http_errors

import logging

log = logging.getLogger(__name__)


class CondaRepoJLAP(RepoInterface):
    def __init__(self, url: str, repodata_fn: Optional[str]) -> None:
        self._url = url
        self._repodata_fn = repodata_fn

        self._log = logging.getLogger(__name__)
        self._stderrlog = logging.getLogger("conda.stderrlog")

    def repodata(self, state: dict) -> str:
        if not context.ssl_verify:
            warnings.simplefilter("ignore", InsecureRequestWarning)

        session = CondaSession()

        headers = {}
        etag = state.get("_etag")
        last_modified = state.get("_mod")
        if etag:
            headers["If-None-Match"] = etag
        if last_modified:
            headers["If-Modified-Since"] = last_modified
        filename = self._repodata_fn

        url = join_url(self._url, filename)
        with conda_http_errors(url, filename):
            timeout = context.remote_connect_timeout_secs, context.remote_read_timeout_secs
            resp = session.get(url, headers=headers, proxies=session.proxies, timeout=timeout)
            if self._log.isEnabledFor(logging.DEBUG):
                self._log.debug(stringify(resp, content_max_len=256))
            resp.raise_for_status()

        if resp.status_code == 304:
            raise Response304ContentUnchanged()

        # We explictly no longer add these tags to the large `resp.content` json
        saved_fields = {"_url": self._url}
        self._add_http_value_to_dict(resp, "Etag", saved_fields, "_etag")
        self._add_http_value_to_dict(resp, "Last-Modified", saved_fields, "_mod")
        self._add_http_value_to_dict(resp, "Cache-Control", saved_fields, "_cache_control")

        state.clear()
        state.update(saved_fields)

        return resp.content

    def _add_http_value_to_dict(self, resp, http_key, d, dict_key):
        value = resp.headers.get(http_key)
        if value:
            d[dict_key] = value
