import logging
import warnings
import pathlib
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
    def __init__(self, url: str, repodata_fn: Optional[str], **kwargs) -> None:
        log.debug("Using CondaRepoJLAP")

        self._url = url
        self._repodata_fn = repodata_fn

        self._log = logging.getLogger(__name__)
        self._stderrlog = logging.getLogger("conda.stderrlog")

        # TODO is there a better way to share these paths
        self._cache_path_json = pathlib.Path(kwargs["cache_path_json"])
        self._cache_path_state = pathlib.Path(kwargs["cache_path_state"])

    def repodata(self, state: dict) -> str:
        console.print_json(data=state)

        repodata_url = f"{self._url}/{self._repodata_fn}"
        jlap_url = f"{self._url}/{self._repodata_fn}"[: -len(".json")] + ".jlap"

        def get_place(url, extra=""):
            if url == repodata_url and extra == "":
                return self._cache_path_json
            raise NotImplementedError("Unexpected URL", url)

        jlapper.request_url_jlap_state(repodata_url, state, get_place=get_place)

        return pathlib.Path(self._cache_path_json).read_text()
