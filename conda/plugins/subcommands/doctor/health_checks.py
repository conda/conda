# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Backend logic implementation for `conda doctor`."""
from __future__ import annotations

import json
from logging import getLogger
from pathlib import Path

from conda.core.envs_manager import get_user_environments_txt_file
from conda.exceptions import CondaError
from conda.gateways.disk.read import compute_sum

logger = getLogger(__name__)

OK_MARK = "✅"
X_MARK = "❌"


def display_report_heading(prefix: str) -> None:
    """Displays our report heading."""
    print(f"Environment Health Report for: {Path(prefix)}\n")


def check_envs_txt_file(prefix: str | Path) -> bool:
    """Checks whether the environment is listed in the environments.txt file"""
    prefix = Path(prefix)
    envs_txt_file = Path(get_user_environments_txt_file())
    try:
        with envs_txt_file.open() as f:
            for line in f.readlines():
                if prefix.samefile(line.strip()):
                    return True
            return False

    except (IsADirectoryError, FileNotFoundError, PermissionError) as err:
        logger.error(
            f"{envs_txt_file} could not be "
            f"accessed because of the following error: {err}"
        )


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


def display_health_checks(prefix: str, verbose: bool = False) -> None:
    """Prints health report."""
    display_report_heading(prefix)
    print("1. Missing Files:\n")
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

    if verbose:
        print("")
    print("2. Altered Files:\n")
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

    present = OK_MARK if check_envs_txt_file(prefix) else X_MARK
    print(f"3. Environment listed in environments.txt file: {present}\n")
