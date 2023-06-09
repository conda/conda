# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import json
from pathlib import Path

OK_MARK = "✅"
REPORT_TITLE = "\nENVIRONMENT HEALTH REPORT\n"
DETAILED_REPORT_TITLE = "\nDETAILED ENVIRONMENT HEALTH REPORT\n"
MISSING_FILES_SUCCESS_MESSAGE = f"{OK_MARK} There are no packages with missing files.\n"


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
