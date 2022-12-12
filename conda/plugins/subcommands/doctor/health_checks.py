# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import json
import pprint

import conda.plugins

from pathlib import Path

# from conda.base import context


def find_packages_with_missing_files(prefix: str):
    """
    List the missing files in the various packages in the environment
    """
    packages = {}
    prefix = Path(prefix)
    conda_meta = prefix.joinpath("conda-meta")
    for file in conda_meta.iterdir():
        if file.name.endswith(".json"):
            packages[file.name] = []
            with file.open() as f:
                data = json.load(f)
            for file_name in data.get("files", ()):
                # Add warnings if json file has missing "files"
                existance = prefix.joinpath(file_name).exists()
                if not existance:
                    packages[file.name].append(file_name)

    return format_message(packages)


def format_message(packages: dict):
    pprint.pprint(packages)


@conda.plugins.hookimpl
def conda_subcommands():
    yield conda.plugins.CondaSubcommand(
        name="doctor",
        summary="A subcommand that displays environment health report",
        action=find_packages_with_missing_files,
    )
