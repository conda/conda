# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Clean path plugin for cached channel notices."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ...notices.cache import get_notices_cache_dir
from .. import hookimpl
from ..types import CondaCleanPath

if TYPE_CHECKING:
    from collections.abc import Iterable


def find_notices_cache_paths(_target_prefix: str) -> Iterable[str]:
    """Return cached notice files that can be removed."""
    cache_dir = get_notices_cache_dir()
    for path in cache_dir.iterdir():
        if path.is_file():
            yield str(path)


@hookimpl
def conda_clean_paths() -> Iterable[CondaCleanPath]:
    yield CondaCleanPath(
        name="notices-cache",
        find=find_notices_cache_paths,
        summary="Remove cached channel notices.",
    )
