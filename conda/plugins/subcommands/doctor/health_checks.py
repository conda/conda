# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import json

import conda.plugins

from pathlib import Path
from rich.console import Console
from rich.table import Table

from conda.base.context import context

active_prefix = context.active_prefix

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

    packages_with_missing_files = {k: v for k, v in packages.items() if v}
    number_of_missing_files = {k: len(v) for k, v in packages_with_missing_files.items()}

    table = Table(title="Packages With Missing Files")

    table.add_column("Package Name", justify="right", style="cyan", no_wrap=True)
    table.add_column("No. of Missing Files", style="magenta")

    for k in number_of_missing_files:
        table.add_row(str(k), str(number_of_missing_files[k]))

    console = Console()
    console.print(table)


def run_health_checks(prefix: str):
    print("\nHealth Report for Your Active Environment\n")
    find_packages_with_missing_files(active_prefix)


@conda.plugins.hookimpl
def conda_subcommands():
    yield conda.plugins.CondaSubcommand(
        name="doctor",
        summary="A subcommand that displays environment health report",
        action=run_health_checks,
    )
