# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import logging
import pathlib

from . import jlapper
from .repo import RepodataIsNone, RepoInterface, conda_http_errors

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


class CondaRepoJLAP(RepoInterface):
    def __init__(self, url: str, repodata_fn: str | None, **kwargs) -> None:
        log.debug("Using CondaRepoJLAP")

        self._url = url
        self._repodata_fn = repodata_fn

        self._log = logging.getLogger(__name__)
        self._stderrlog = logging.getLogger("conda.stderrlog")

        # TODO is there a better way to share these paths
        self._cache_path_json = pathlib.Path(kwargs["cache_path_json"])
        self._cache_path_state = pathlib.Path(kwargs["cache_path_state"])

    def repodata(self, state: dict) -> str | None:
        console.print_json(data=state)

        repodata_url = f"{self._url}/{self._repodata_fn}"
        # jlap_url = f"{self._url}/{self._repodata_fn}"[: -len(".json")] + ".jlap"

        def get_place(url, extra=""):
            if url == repodata_url and extra == "":
                return self._cache_path_json
            raise NotImplementedError("Unexpected URL", url)

        try:
            with conda_http_errors(self._url, self._repodata_fn):
                jlapper.request_url_jlap_state(repodata_url, state, get_place=get_place)
        except RepodataIsNone:
            return None

        # XXX do headers come from a different place when fetched with jlap vs
        # fetched with complete download?
        headers = state.get("jlap", {}).get("headers")
        if headers:
            state["_etag"] = headers.get("etag")
            state["_mod"] = headers.get("last-modified")
            state["_cache_control"] = headers.get("cache-control")

        return pathlib.Path(self._cache_path_json).read_text()
