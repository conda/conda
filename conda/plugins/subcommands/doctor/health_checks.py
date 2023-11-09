# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Backend logic implementation for `conda doctor`."""
from __future__ import annotations

import json
import os
from logging import getLogger
from pathlib import Path

from ....base.context import context
from ....core.envs_manager import get_user_environments_txt_file
from ....deprecations import deprecated
from ....exceptions import CondaError
from ....gateways.disk.read import compute_sum
from ... import CondaHealthCheck, hookimpl

logger = getLogger(__name__)

OK_MARK = "✅"
X_MARK = "❌"


@deprecated("24.3", "24.9")
def display_report_heading(prefix: str) -> None:
    """Displays our report heading."""
    print(f"Environment Health Report for: {Path(prefix)}\n")


def check_envs_txt_file(prefix: str | os.PathLike | Path) -> bool:
    """Checks whether the environment is listed in the environments.txt file"""
    prefix = Path(prefix)
    envs_txt_file = Path(get_user_environments_txt_file())

    def samefile(path1: Path, path2: Path) -> bool:
        try:
            return path1.samefile(path2)
        except FileNotFoundError:
            # FileNotFoundError: path doesn't exist
            return path1 == path2

    try:
        for line in envs_txt_file.read_text().splitlines():
            stripped_line = line.strip()
            if stripped_line and samefile(prefix, Path(stripped_line)):
                return True
    except (IsADirectoryError, FileNotFoundError, PermissionError) as err:
        logger.error(
            f"{envs_txt_file} could not be "
            f"accessed because of the following error: {err}"
        )
    return False


def find_packages_with_missing_files(prefix: str | Path) -> dict[str, list[str]]:
    """Finds packages listed in conda-meta which have missing files."""
    packages_with_missing_files = {}
    prefix = Path(prefix)
    for file in (prefix / "conda-meta").glob("*.json"):
        for file_name in json.loads(file.read_text()).get("files", []):
            # Add warnings if json file has missing "files"
            if not (prefix / file_name).exists():
                packages_with_missing_files.setdefault(file.stem, []).append(file_name)
    return packages_with_missing_files


def find_altered_packages(prefix: str | Path) -> dict[str, list[str]]:
    """Finds altered packages"""
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


@deprecated("24.3", "24.9")
def display_health_checks(prefix: str, verbose: bool = False) -> None:
    """Prints health report."""
    print(f"Environment Health Report for: {prefix}\n")
    context.plugin_manager.invoke_health_checks(prefix, verbose)


def missing_files(prefix: str, verbose: bool) -> None:
    print("Missing Files:\n")
    missing_files = find_packages_with_missing_files(prefix)
    if missing_files:
        for package_name, missing_files in missing_files.items():
            if verbose:
                delimiter = "\n  "
                print(f"{package_name}:{delimiter}{delimiter.join(missing_files)}")
            else:
                print(f"{package_name}: {len(missing_files)}\n")
    else:
        print(f"{OK_MARK} There are no packages with missing files.\n")


def altered_files(prefix: str, verbose: bool) -> None:
    print("Altered Files:\n")
    altered_packages = find_altered_packages(prefix)
    if altered_packages:
        for package_name, altered_files in altered_packages.items():
            if verbose:
                delimiter = "\n  "
                print(f"{package_name}:{delimiter}{delimiter.join(altered_files)}\n")
            else:
                print(f"{package_name}: {len(altered_files)}\n")
    else:
        print(f"{OK_MARK} There are no packages with altered files.\n")


def env_txt_check(prefix: str, verbose: bool) -> None:
    present = OK_MARK if check_envs_txt_file(prefix) else X_MARK
    print(f"Environment listed in environments.txt file: {present}\n")


@hookimpl
def conda_health_checks():
    yield CondaHealthCheck(name="Missing Files", action=missing_files)
    yield CondaHealthCheck(name="Altered Files", action=altered_files)
    yield CondaHealthCheck(name="Environment.txt File Check", action=env_txt_check)
