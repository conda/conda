# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import logging
from pathlib import Path

from conda.gateways.connection.session import CondaSession

from .. import (
    CACHE_CONTROL_KEY,
    ETAG_KEY,
    LAST_MODIFIED_KEY,
    URL_KEY,
    RepodataCache,
    RepodataOnDisk,
    RepodataState,
    RepoInterface,
    Response304ContentUnchanged,
    conda_http_errors,
)
from . import fetch

log = logging.getLogger(__name__)


class JlapRepoInterface(RepoInterface):
    def __init__(
        self,
        url: str,
        repodata_fn: str | None,
        cache_path_json: str | Path,
        cache_path_state: str | Path,
        cache: RepodataCache,
        **kwargs,
    ) -> None:
        log.debug("Using CondaRepoJLAP")

        # TODO is there a better way to share these paths
        self._cache_path_json = Path(cache_path_json)
        self._cache_path_state = Path(cache_path_state)

        # replaces self._cache_path_json/state
        self._cache = cache

        self._url = url
        self._repodata_fn = repodata_fn

        self._log = logging.getLogger(__name__)
        self._stderrlog = logging.getLogger("conda.stderrlog")

    def repodata(self, state: dict | RepodataState) -> str | None:
        """
        Fetch newest repodata if necessary.

        Always writes to ``cache_path_json``.
        """
        self.repodata_parsed(state)
        raise RepodataOnDisk()

    def repodata_parsed(self, state: dict | RepodataState) -> dict | None:
        """
        JLAP has to parse the JSON anyway.

        Use this to avoid a redundant parse when repodata is updated.

        When repodata is not updated, it doesn't matter whether this function or
        the caller reads from a file.
        """
        session = CondaSession()

        repodata_url = f"{self._url}/{self._repodata_fn}"

        # XXX won't modify caller's state dict
        state_ = RepodataState(dict=state)

        try:
            with conda_http_errors(self._url, self._repodata_fn):
                repodata_json_or_none = fetch.request_url_jlap_state(
                    repodata_url, state_, session=session, cache=self._cache
                )
        except fetch.Jlap304NotModified:
            raise Response304ContentUnchanged()

        # XXX update caller's state dict-or-RepodataState
        state.update(state_)

        state[URL_KEY] = self._url
        headers = state.get("jlap", {}).get(
            "headers"
        )  # XXX overwrite headers in jlapper.request_url_jlap_state
        if headers:
            state[ETAG_KEY] = headers.get("etag")
            state[LAST_MODIFIED_KEY] = headers.get("last-modified")
            state[CACHE_CONTROL_KEY] = headers.get("cache-control")

        if repodata_json_or_none is None:  # common
            # Indicate that subdir_data mustn't rewrite cache_path_json
            raise RepodataOnDisk()
        else:
            return repodata_json_or_none
