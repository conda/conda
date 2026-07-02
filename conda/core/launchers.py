# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Helpers for locating Windows entry point launchers."""

from __future__ import annotations

from logging import getLogger
from os.path import isfile, join
from typing import TYPE_CHECKING

from ..base.context import context
from ..common.io import dashlist
from .prefix_data import PrefixData

if TYPE_CHECKING:
    from collections.abc import Iterable
    from os import PathLike

log = getLogger(__name__)

CONDA_LAUNCHERS_PACKAGE_NAME = "conda-launchers"


def get_windows_launcher_stub_path(
    subdir: str | None = None,
    *,
    source_prefixes: Iterable[str | PathLike[str]],
) -> str:
    """Return the source path for a Windows Python entry point launcher."""
    import conda_launchers

    subdir = subdir or context.subdir
    supported_subdirs = conda_launchers.get_supported_subdirs()
    try:
        launcher_short_path = conda_launchers.get_launcher_short_path(subdir)
    except ValueError as exc:
        raise NotImplementedError(
            f"Windows entry point stub not available for subdir {subdir!r}. "
            f"Supported: {dashlist(supported_subdirs)}."
        ) from exc

    for prefix in source_prefixes:
        try:
            record = PrefixData(prefix).get(CONDA_LAUNCHERS_PACKAGE_NAME, None)
        except OSError:
            log.debug("Could not read prefix metadata for %s", prefix, exc_info=True)
            continue

        if record is None:
            continue

        package_paths = set(record.files or ())
        if paths_data := getattr(record, "paths_data", None):
            package_paths.update(path_data.path for path_data in paths_data.paths)
        if launcher_short_path.replace("\\", "/") not in {
            path.replace("\\", "/") for path in package_paths
        }:
            continue

        launcher_path = join(prefix, launcher_short_path)
        if isfile(launcher_path):
            return launcher_path

    raise FileNotFoundError(
        f"Could not find Windows entry point stub for subdir {subdir!r}: "
        f"{launcher_short_path!r} from {CONDA_LAUNCHERS_PACKAGE_NAME!r}."
    )
