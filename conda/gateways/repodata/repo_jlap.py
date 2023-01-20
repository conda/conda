# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import logging
from pathlib import Path

from conda.gateways.connection.session import CondaSession

from . import RepoInterface, conda_http_errors, jlapper

log = logging.getLogger(__name__)

try:
    from rich.console import Console

    console = Console()
except ImportError:
    import pprint

    class console:
        @staticmethod
        def print_json(data={}):
            log.info("%s", pprint.pformat(data))


class JlapRepoInterface(RepoInterface):
    def __init__(
        self,
        url: str,
        repodata_fn: str | None,
        cache_path_json: str | Path,
        cache_path_state: str | Path,
        **kwargs,
    ) -> None:
        log.debug("Using CondaRepoJLAP")

        # TODO is there a better way to share these paths
        self._cache_path_json = Path(cache_path_json)
        self._cache_path_state = Path(cache_path_state)

        self._url = url
        self._repodata_fn = repodata_fn

        self._log = logging.getLogger(__name__)
        self._stderrlog = logging.getLogger("conda.stderrlog")

    def repodata(self, state: dict) -> str | None:
        console.print_json(data=state)

        session = CondaSession()

        repodata_url = f"{self._url}/{self._repodata_fn}"
        # jlap_url = f"{self._url}/{self._repodata_fn}"[: -len(".json")] + ".jlap"

        def get_place(url, extra=""):
            if url == repodata_url and extra == "":
                return self._cache_path_json
            raise NotImplementedError("Unexpected URL", url)

        with conda_http_errors(self._url, self._repodata_fn):
            jlapper.request_url_jlap_state(
                repodata_url, state, get_place=get_place, session=session
            )

        state["_url"] = self._url
        headers = state.get("jlap", {}).get(
            "headers"
        )  # XXX overwrite headers in jlapper.request_url_jlap_state
        if headers:
            state["_etag"] = headers.get("etag")
            state["_mod"] = headers.get("last-modified")
            state["_cache_control"] = headers.get("cache-control")

        # XXX SubdirData._load will immediately rewrite this because it doesn't
        # know we saved it; is this still a valid concern on "304 not modified"??
        return Path(self._cache_path_json).read_text()
