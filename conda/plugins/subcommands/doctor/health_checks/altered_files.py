# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Health check: Altered files in packages."""

from __future__ import annotations

from logging import getLogger
from pathlib import Path
from typing import TYPE_CHECKING

from .....base.constants import OK_MARK, X_MARK
from .....cli.install import reinstall_packages
from .....common.serialize import json
from .....exceptions import CondaError
from .....gateways.disk.read import compute_sum
from .... import hookimpl
from ....types import CondaHealthCheck
from .missing_files import excluded_files_check

if TYPE_CHECKING:
    from argparse import Namespace
    from collections.abc import Iterable

    from ....types import ConfirmCallback


logger = getLogger(__name__)


def find_altered_packages(prefix: str | Path) -> dict[str, list[str]]:
    """Finds packages with altered files (checksum mismatch)."""
    altered_packages = {}
    prefix = Path(prefix)

    for file in (prefix / "conda-meta").glob("*.json"):
        try:
            metadata = json.loads(file.read_text())
        except Exception as exc:
            logger.error(
                f"Could not load the json file {file} because of the following error: {exc}."
            )
            continue

        try:
            paths_data = metadata["paths_data"]
            paths = paths_data["paths"]
        except KeyError:
            continue

        if paths_data.get("paths_version") != 1:
            continue

        for path in paths:
            _path = path.get("_path")
            if excluded_files_check(_path):
                continue

            old_sha256 = path.get("sha256_in_prefix")
            if _path is None or old_sha256 is None:
                continue

            file_location = prefix / _path
            if not file_location.is_file():
                continue

            try:
                new_sha256 = compute_sum(file_location, "sha256")
            except OSError as err:
                raise CondaError(
                    f"Could not generate checksum for file {file_location} "
                    f"because of the following error: {err}."
                )

            if old_sha256 != new_sha256:
                altered_packages.setdefault(file.stem, []).append(_path)

    return altered_packages


def altered_files(prefix: str, verbose: bool) -> None:
    """Health check action: Report packages with altered files."""
    altered = find_altered_packages(prefix)
    if altered:
        print(f"{X_MARK} Altered Files:\n")
        for package_name, files in altered.items():
            if verbose:
                delimiter = "\n  "
                print(f"{package_name}:{delimiter}{delimiter.join(files)}\n")
            else:
                print(f"{package_name}: {len(files)}\n")
    else:
        print(f"{OK_MARK} There are no packages with altered files.\n")


def fix_altered_files(prefix: str, args: Namespace, confirm: ConfirmCallback) -> int:
    """Fix altered files by reinstalling affected packages."""
    altered = find_altered_packages(prefix)

    if not altered:
        print("No packages with altered files found.")
        return 0

    print(f"Found {len(altered)} package(s) with altered files:")
    for pkg_name, files in sorted(altered.items()):
        print(f"  {pkg_name}: {len(files)} altered file(s)")

    print()
    confirm("Reinstall these packages to restore original files?")

    specs = list(altered.keys())
    return reinstall_packages(args, specs, force_reinstall=True)


@hookimpl
def conda_health_checks() -> Iterable[CondaHealthCheck]:
    """Register the altered files health check."""
    yield CondaHealthCheck(
        name="altered-files",
        action=altered_files,
        fixer=fix_altered_files,
        summary="Detect packages with modified files",
        fix="Reinstall affected packages",
    )
