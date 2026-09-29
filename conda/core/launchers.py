# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Locate and verify Windows entry point launchers."""

from __future__ import annotations

from os.path import isfile, join, normpath
from typing import TYPE_CHECKING

from .. import CONDA_PACKAGE_ROOT
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
    """Return the target Python's launcher path and expected SHA-256."""
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
    launcher_info = next(
        (
            info
            for info in source_package_infos
            if info.repodata_record.name == "conda-launchers"
        ),
        None,
    )
    if launcher_info is not None:
        if launcher_info.repodata_record.subdir != "noarch":
            raise SafetyError("Expected conda-launchers from the noarch subdir.")
        if launcher := _find_launcher(
            launcher_info.extracted_package_dir, launcher_info.paths_data, short_path
        ):
            return launcher
    else:
        for prefix in source_prefixes:
            record = PrefixData(prefix).get("conda-launchers", None)
            if record is None:
                continue
            if record.subdir != "noarch":
                raise SafetyError("Expected conda-launchers from the noarch subdir.")
            if launcher := _find_launcher(prefix, record.paths_data, short_path):
                return launcher

    # Retain the bundled stub until defaults publishes a 32-bit launcher.
    if subdir == "win-32":
        path = join(CONDA_PACKAGE_ROOT, "shell", "cli-32.exe")
        if not isfile(path):
            raise FileNotFoundError(f"Missing bundled Windows launcher {path!r}.")
        return (
            path,
            "0170dda609519c088b1e4619a1e1d15a01701a6c514bb55f99a85fcbbd541631",
        )

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
        path = normpath(join(prefix, short_path))
        if not isfile(path):
            raise FileNotFoundError(f"Missing conda-launchers file {path!r}.")
        if not getattr(path_data, "sha256", None):
            raise SafetyError(
                f"Missing SHA-256 for conda-launchers file {short_path!r}."
            )
        return path, path_data.sha256
    return None


def verify_windows_launcher(path: str, sha256: str) -> None:
    """Verify the expected SHA-256 immediately before copying a launcher."""
    if not sha256 or compute_sum(path, "sha256") != sha256:
        raise SafetyError(f"SHA-256 mismatch for launcher file {path!r}.")
