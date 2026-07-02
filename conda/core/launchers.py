# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Helpers for locating Windows entry point launchers."""

from __future__ import annotations

from logging import getLogger
from os.path import isfile, join
from typing import TYPE_CHECKING

from .. import CONDA_PACKAGE_ROOT
from ..base.constants import WINDOWS_LAUNCHER_STUB_PATH
from ..base.context import context
from ..common.io import dashlist
from .prefix_data import PrefixData

try:
    from conda_launchers import (
        get_launcher_short_path as _conda_launchers_get_launcher_short_path,
    )
    from conda_launchers import (
        get_supported_subdirs as _conda_launchers_get_supported_subdirs,
    )
except ImportError:  # pragma: no cover - exercised through fallback tests
    _conda_launchers_get_launcher_short_path = None
    _conda_launchers_get_supported_subdirs = None

if TYPE_CHECKING:
    from collections.abc import Iterable
    from os import PathLike

log = getLogger(__name__)

CONDA_LAUNCHERS_PACKAGE_NAME = "conda-launchers"
_CONDA_LAUNCHERS_WINDOWS_STUB_PATH = {
    "win-32": "Scripts/cli-32.exe",
    "win-64": "Scripts/cli-64.exe",
    "win-arm64": "Scripts/cli-arm64.exe",
}


def get_windows_launcher_stub_path(
    subdir: str | None = None,
    *,
    prefixes: Iterable[str | PathLike[str]] = (),
) -> str:
    """Return the best source path for a Windows Python entry point launcher."""
    subdir = subdir or context.subdir
    launcher_short_path = _get_conda_launchers_launcher_short_path(subdir)
    for prefix in (*prefixes, context.conda_prefix):
        if launcher_path := _get_conda_launchers_file(prefix, launcher_short_path):
            return launcher_path

    fallback_short_path = WINDOWS_LAUNCHER_STUB_PATH.get(subdir)
    if fallback_short_path:
        fallback_path = join(CONDA_PACKAGE_ROOT, fallback_short_path)
        if isfile(fallback_path):
            return fallback_path

    raise FileNotFoundError(
        f"Could not find Windows entry point stub for subdir {subdir!r}: "
        f"{launcher_short_path!r} from {CONDA_LAUNCHERS_PACKAGE_NAME!r} or "
        f"{fallback_short_path or 'no bundled fallback'} under conda."
    )


def _get_conda_launchers_file(
    prefix: str | PathLike[str],
    launcher_short_path: str,
) -> str | None:
    try:
        record = PrefixData(prefix).get(CONDA_LAUNCHERS_PACKAGE_NAME, None)
    except OSError:
        log.debug("Could not read prefix metadata for %s", prefix, exc_info=True)
        return None

    if record is None:
        return None

    package_paths = set(record.files or ())
    if paths_data := getattr(record, "paths_data", None):
        package_paths.update(path_data.path for path_data in paths_data.paths)
    if _normalize_path(launcher_short_path) not in {
        _normalize_path(path) for path in package_paths
    }:
        return None

    launcher_path = join(prefix, launcher_short_path)
    return launcher_path if isfile(launcher_path) else None


def _normalize_path(path: str) -> str:
    return path.replace("\\", "/")


def _get_conda_launchers_launcher_short_path(subdir: str) -> str:
    try:
        if _conda_launchers_get_launcher_short_path:
            return _conda_launchers_get_launcher_short_path(subdir)
        return _CONDA_LAUNCHERS_WINDOWS_STUB_PATH[subdir]
    except (KeyError, ValueError) as exc:
        raise NotImplementedError(
            f"Windows entry point stub not available for subdir {subdir!r}. "
            f"Supported: {dashlist(_get_supported_conda_launchers_subdirs())}."
        ) from exc


def _get_supported_conda_launchers_subdirs() -> tuple[str, ...]:
    if _conda_launchers_get_supported_subdirs:
        return _conda_launchers_get_supported_subdirs()
    return tuple(_CONDA_LAUNCHERS_WINDOWS_STUB_PATH)
