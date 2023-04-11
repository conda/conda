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
    """
    Displays our report heading
    """
    print("-" * 20)
    print(REPORT_TITLE)
    print(f"Environment Name: {Path(prefix).name}\n")


def get_number_of_missing_files(prefix: str) -> dict[str, int]:
    """
    Returns a dictionary with packages and the number of missing files in them
    """
    packages_with_missing_files = find_packages_with_missing_files(prefix)

    return {k: len(v) for k, v in packages_with_missing_files.items()}


def find_packages_with_missing_files(prefix: str | Path) -> dict[str, list[str]]:
    """
    Finds packages listed in conda-meta which have missing files
    """
    packages = {}
    prefix = Path(prefix)
    conda_meta = prefix.joinpath("conda-meta")
    for file in conda_meta.iterdir():
        if file.name.endswith(".json"):
            name = file.stem
            packages[name] = []
            data = json.loads(file.read_text())
            for file_name in data.get("files", ()):
                # Add warnings if json file has missing "files"
                if not (prefix / file_name).exists():
                    packages[name].append(file_name)

    packages_with_missing_files = {k: v for k, v in packages.items() if v}

    return packages_with_missing_files


def display_health_checks(prefix: str, verbose: bool) -> None:
    """
    Prints health report
    """
    display_report_heading(prefix)
    missing_files = find_packages_with_missing_files(prefix)
    if missing_files:
        print("Missing Files\n")
        for file, files in missing_files.items():
            if verbose:
                files_as_str = "\n".join(files)
                print(f"{file}:\n{files_as_str}")
            else:
                print(f"{file}: {len(files)}")

        print("\n")
    else:
        print(MISSING_FILES_SUCCESS_MESSAGE)
