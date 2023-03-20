# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import json

from pathlib import Path

from conda.base.context import context

OK_MARK = "✅"
REPORT_TITLE = "\nENVIRONMENT HEALTH REPORT\n"
DETAILED_REPORT_TITLE = "\nDETAILED ENVIRONMENT HEALTH REPORT\n"
MISSING_FILES_SUCCESS_MESSAGE = f"{OK_MARK} There are no packages with missing files.\n"


def display_report_heading() -> None:
    environment = Path(context.active_prefix)
    environment_name = environment.name
    print("-" * 20)
    print(REPORT_TITLE)
    print(f"Environment Name: {environment_name}\n")


def get_number_of_missing_files(prefix: str) -> dict[str, int]:
    """
    Returns a dictionary with packages and the number of missing files in them
    """
    packages_with_missing_files = find_packages_with_missing_files(prefix)

    return {k: len(v) for k, v in packages_with_missing_files.items()}


def find_packages_with_missing_files(prefix: str) -> dict[str, list[str]]:
    """
    Finds packages listed in conda-meta which have missing files
    """
    packages = {}
    prefix = Path(prefix)
    conda_meta = prefix.joinpath("conda-meta")
    for file in conda_meta.iterdir():
        if file.name.endswith(".json"):
            name = str(file.name)[:-5]
            packages[name] = []
            with file.open() as f:
                data = json.load(f)
            for file_name in data.get("files", ()):
                # Add warnings if json file has missing "files"
                existence = prefix.joinpath(file_name).exists()
                if not existence:
                    packages[name].append(file_name)

    packages_with_missing_files = {k: v for k, v in packages.items() if v}

    return packages_with_missing_files


def display_health_checks(verbose=False) -> None:
    """
    Prints health report
    """
    display_report_heading()
    number_of_missing_files = get_number_of_missing_files(context.active_prefix)
    if number_of_missing_files:
        print("Number of Missing Files\n")
        for file, number_of_files in number_of_missing_files.items():
            print(f"{file}:\t{str(number_of_files)}")

        print("\n")
    else:
        print(MISSING_FILES_SUCCESS_MESSAGE)


def display_detailed_health_checks() -> None:
    """
    Prints detailed health report
    """
    display_report_heading()
    names_of_missing_files = find_packages_with_missing_files(context.active_prefix)
    if names_of_missing_files:
        print("Missing Files\n")
        for file, number_of_files in names_of_missing_files.items():
            print(f"{file}:\t{str(number_of_files)}")

        print("\n")
    else:
        print(MISSING_FILES_SUCCESS_MESSAGE)
