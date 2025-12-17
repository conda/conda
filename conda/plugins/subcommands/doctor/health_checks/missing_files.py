# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Health check: Missing files in packages."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from .....base.context import context
from .....common.serialize import json
from .....reporters import confirm_yn
from .... import hookimpl
from ....types import CondaHealthCheck
from ._common import OK_MARK, X_MARK, excluded_files_check, reinstall_packages

if TYPE_CHECKING:
    from argparse import Namespace
    from collections.abc import Iterable


def find_packages_with_missing_files(prefix: str | Path) -> dict[str, list[str]]:
    """Finds packages listed in conda-meta which have missing files."""
    packages_with_missing_files = {}
    prefix = Path(prefix)
    for file in (prefix / "conda-meta").glob("*.json"):
        for file_name in json.loads(file.read_text()).get("files", []):
            if (
                not excluded_files_check(file_name)
                and not (prefix / file_name).exists()
            ):
                packages_with_missing_files.setdefault(file.stem, []).append(file_name)
    return packages_with_missing_files


def missing_files(prefix: str, verbose: bool) -> None:
    """Health check action: Report packages with missing files."""
    missing = find_packages_with_missing_files(prefix)
    if missing:
        print(f"{X_MARK} Missing Files:\n")
        for package_name, files in missing.items():
            if verbose:
                delimiter = "\n  "
                print(f"{package_name}:{delimiter}{delimiter.join(files)}")
            else:
                print(f"{package_name}: {len(files)}\n")
    else:
        print(f"{OK_MARK} There are no packages with missing files.\n")


def fix_missing_files(prefix: str, args: Namespace) -> int:
    """Fix missing files by reinstalling affected packages."""
    packages_with_missing = find_packages_with_missing_files(prefix)

    if not packages_with_missing:
        print("No packages with missing files found.")
        return 0

    print(f"Found {len(packages_with_missing)} package(s) with missing files:")
    for pkg_name, files in sorted(packages_with_missing.items()):
        print(f"  {pkg_name}: {len(files)} missing file(s)")

    print()
    confirm_yn(
        "Reinstall these packages to restore missing files?",
        default="no",
        dry_run=context.dry_run,
    )

    specs = list(packages_with_missing.keys())
    return reinstall_packages(args, specs, force_reinstall=True)


@hookimpl
def conda_health_checks() -> Iterable[CondaHealthCheck]:
    """Register the missing files health check."""
    yield CondaHealthCheck(
        name="Missing Files",
        action=missing_files,
        fix=fix_missing_files,
        summary="Reinstall packages with missing files",
    )
