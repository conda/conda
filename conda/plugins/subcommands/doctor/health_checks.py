# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import json
from logging import getLogger
from pathlib import Path

from conda.exceptions import CondaError
from conda.gateways.disk.read import compute_sum

logger = getLogger("health_checks")

OK_MARK = "✅"
REPORT_TITLE = "\nENVIRONMENT HEALTH REPORT\n"
DETAILED_REPORT_TITLE = "\nDETAILED ENVIRONMENT HEALTH REPORT\n"
MISSING_FILES_SUCCESS_MESSAGE = f"{OK_MARK} There are no packages with missing files.\n"
ALTERED_FILES_SUCCESS_MESSAGE = f"{OK_MARK} There are no packages with altered files.\n"


def display_report_heading(prefix: str) -> None:
    """Displays our report heading."""
    print("-" * 20)
    print(REPORT_TITLE)
    print(f"Environment Name: {Path(prefix).name}\n")


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
            data = json.loads(file.read_text())
        except Exception:
            logger.error("Could not load the json file {file}")

        required_data = data["paths_data"]["paths"]

        for path in required_data:
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


def display_health_checks(prefix: str, verbose: bool) -> None:
    """Prints health report."""
    display_report_heading(prefix)
    missing_files = find_packages_with_missing_files(prefix)
    if missing_files:
        print("Missing Files\n")
        for file, files in missing_files.items():
            if verbose:
                delimiter = "\n  "
                print(f"{file}:{delimiter}{delimiter.join(files)}\n")
            else:
                print(f"{file}: {len(files)}")

        print("\n")
    else:
        print(MISSING_FILES_SUCCESS_MESSAGE)

    altered_packages = find_altered_packages(prefix)
    if altered_packages:
        print("Altered Files\n")
        for file, files in altered_packages.items():
            if verbose:
                delimiter = "\n "
                print(f"{file}:{delimiter}{delimiter.join(files)}\n")
            else:
                print(f"{file}: {len(files)}")

        print("\n")
    else:
        print(ALTERED_FILES_SUCCESS_MESSAGE)
