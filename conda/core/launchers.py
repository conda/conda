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

    from ..models.package_info import PackageInfo

log = getLogger(__name__)

CONDA_LAUNCHERS_PACKAGE_NAME = "conda-launchers"


def get_windows_launcher_stub_path(
    subdir: str | None = None,
    *,
    source_prefixes: Iterable[str | PathLike[str]],
    source_package_infos: Iterable[PackageInfo] = (),
) -> str:
    """Return the source path for a Windows Python entry point launcher."""
    # Import lazily so non-Windows imports of conda do not need the Windows-only
    # conda-launchers package.
    import conda_launchers

    subdir = subdir or context.subdir
    # Let conda-launchers own the subdir-to-filename mapping.
    supported_subdirs = conda_launchers.get_supported_subdirs()
    try:
        launcher_short_path = conda_launchers.get_launcher_short_path(subdir)
    except ValueError as exc:
        raise NotImplementedError(
            f"Windows entry point stub not available for subdir {subdir!r}. "
            f"Supported: {dashlist(supported_subdirs)}."
        ) from exc

    for package_info in source_package_infos:
        if package_info.repodata_record.name != CONDA_LAUNCHERS_PACKAGE_NAME:
            continue

        # A package being linked does not have prefix metadata yet; use the
        # extracted package manifest instead.
        package_paths = {
            path_data.path.replace("\\", "/")
            for path_data in package_info.paths_data.paths
        }
        if launcher_short_path.replace("\\", "/") not in package_paths:
            continue

        launcher_path = join(package_info.extracted_package_dir, launcher_short_path)
        if isfile(launcher_path):
            return launcher_path

    # Only search explicit source prefixes; the target prefix is not a source
    # unless the caller intentionally passes it.
    for prefix in source_prefixes:
        try:
            record = PrefixData(prefix).get(CONDA_LAUNCHERS_PACKAGE_NAME, None)
        except OSError:
            log.debug("Could not read prefix metadata for %s", prefix, exc_info=True)
            continue

        if record is None:
            continue

        # Prefix metadata proves package ownership; it does not choose the path.
        package_paths = set(record.files or ())
        if paths_data := getattr(record, "paths_data", None):
            package_paths.update(path_data.path for path_data in paths_data.paths)
        # Conda package records use POSIX separators, but normalize defensively.
        if launcher_short_path.replace("\\", "/") not in {
            path.replace("\\", "/") for path in package_paths
        }:
            continue

        launcher_path = join(prefix, launcher_short_path)
        # Ownership is not enough if the file was removed after linking.
        if isfile(launcher_path):
            return launcher_path

    raise FileNotFoundError(
        f"Could not find Windows entry point stub for subdir {subdir!r}: "
        f"{launcher_short_path!r} from {CONDA_LAUNCHERS_PACKAGE_NAME!r}."
    )
