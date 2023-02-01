# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import json

from pathlib import Path
from datetime import date

from conda.base.context import context

active_prefix = context.active_prefix

REPORT_TITLE = "\nENVIRONMENT HEALTH REPORT\n"
DETAILED_REPORT_TITLE = "\nDETAILED ENVIRONMENT HEALTH REPORT\n"
OK_MARK = "✅"


def generate_report_heading(prefix: str, report_title: str):
    environment = Path(active_prefix)
    environment_name = environment.name
    print("-" * 20)
    print(REPORT_TITLE)
    today = str(date.today())
    print(f"Date: {today}")
    print(f"Name of the patient: {environment_name}\n")

def get_number_of_missing_files(prefix: str):
    """Print number of missing files for each package"""
    packages_with_missing_files = find_packages_with_missing_files(prefix)

    if packages_with_missing_files:
        number_of_missing_files = {k: len(v) for k, v in packages_with_missing_files.items()}
        return number_of_missing_files
    else:
        return packages_with_missing_files


def get_names_of_missing_files(prefix: str):
    """Print the names of missing files in each package"""
    packages_with_missing_files = find_packages_with_missing_files(prefix)

    return packages_with_missing_files


def find_packages_with_missing_files(prefix: str):
    """
    Finds packages listed in conda-meta with missing files
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
                existance = prefix.joinpath(file_name).exists()
                if not existance:
                    packages[name].append(file_name)

    packages_with_missing_files = {k: v for k, v in packages.items() if v}

    return packages_with_missing_files


def run_health_checks(prefix: str):
    generate_report_heading(active_prefix, REPORT_TITLE)
    number_of_missing_files = get_number_of_missing_files(active_prefix)
    if number_of_missing_files:
        print("Number of Missing Files\n")
        for k in number_of_missing_files:
            print(f"{k}:\t{str(number_of_missing_files[k])}")

        print("\n")
    else:
        print(f"{OK_MARK} There are no packages with missing files.\n")


def run_detailed_health_checks(prefix: str):
    generate_report_heading(active_prefix, DETAILED_REPORT_TITLE)
    names_of_missing_files = get_names_of_missing_files(active_prefix)
    if names_of_missing_files:
        print("Missing Files\n")
        for k in names_of_missing_files:
            print(f"{k}:\t{str(names_of_missing_files[k])}")

        print("\n")
    else:
        print(f"{OK_MARK} There are no packages with missing files.\n")
