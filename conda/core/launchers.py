# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Locate and verify Windows entry point launchers from conda-launchers."""

from __future__ import annotations

from os.path import isfile, join
from typing import TYPE_CHECKING

from ..base.constants import WINDOWS_LAUNCHER_STUB_PATH
from ..base.context import context
from ..common.io import dashlist
from ..exceptions import SafetyError
from ..gateways.disk.read import compute_sum
from .prefix_data import PrefixData

if TYPE_CHECKING:
    from collections.abc import Iterable
    from os import PathLike

    from ..models.package_info import PackageInfo
    from ..models.records import PathsData


def get_windows_launcher_stub(
    target_prefix: str | PathLike[str],
    *,
    source_prefixes: Iterable[str | PathLike[str]],
    source_package_infos: Iterable[PackageInfo] = (),
) -> tuple[str, str]:
    """Return the target Python's launcher path and its package SHA-256."""
    source_package_infos = tuple(source_package_infos)
    python_record = next(
        (
            info.repodata_record
            for info in source_package_infos
            if info.repodata_record.name == "python"
        ),
        None,
    ) or PrefixData(target_prefix).get("python", None)
    subdir = python_record.subdir if python_record else context.subdir
    try:
        short_path = WINDOWS_LAUNCHER_STUB_PATH[subdir]
    except KeyError as exc:
        raise NotImplementedError(
            f"Windows entry point stub not available for subdir {subdir!r}. "
            f"Supported: {dashlist(WINDOWS_LAUNCHER_STUB_PATH)}."
        ) from exc

    # Prefer the extracted package during upgrades, before installed files are unlinked.
    for info in source_package_infos:
        if info.repodata_record.name == "conda-launchers":
            if launcher := _find_launcher(
                info.extracted_package_dir, info.paths_data, short_path
            ):
                return launcher

    for prefix in source_prefixes:
        record = PrefixData(prefix).get("conda-launchers", None)
        if record is not None:
            if launcher := _find_launcher(prefix, record.paths_data, short_path):
                return launcher

    raise FileNotFoundError(
        f"Could not find {short_path!r} in the conda-launchers package. "
        f"Install conda-launchers with support for {subdir!r}."
    )


def _find_launcher(
    prefix: str | PathLike[str], paths_data: PathsData | None, short_path: str
) -> tuple[str, str] | None:
    for path_data in paths_data.paths if paths_data else ():
        if path_data.path.replace("\\", "/") != short_path:
            continue
        path = join(prefix, short_path)
        if not isfile(path):
            return None
        if not getattr(path_data, "sha256", None):
            raise SafetyError(
                f"Missing SHA-256 for conda-launchers file {short_path!r}."
            )
        return path, path_data.sha256
    return None


def verify_windows_launcher(path: str, sha256: str) -> None:
    """Verify the package SHA-256 immediately before copying a launcher."""
    if not sha256 or compute_sum(path, "sha256") != sha256:
        raise SafetyError(f"SHA-256 mismatch for conda-launchers file {path!r}.")
