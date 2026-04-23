# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Health check: Report packages not installed by conda"""

from __future__ import annotations

import subprocess
import sys
from typing import TYPE_CHECKING

from .....base.constants import OK_MARK, X_MARK
from .....cli.install import reinstall_packages
from .....core.prefix_data import PrefixData
from .... import hookimpl
from ....types import CondaHealthCheck

if TYPE_CHECKING:
    from argparse import Namespace
    from collections.abc import Iterable

    from ....types import ConfirmCallback


def find_external_packages(prefix: str) -> list[PrefixData]:
    prefix_data = PrefixData(prefix, interoperability=True)
    external_packages = prefix_data.get_python_packages()
    return external_packages


def print_external_packages(prefix: str, verbose: bool) -> None:
    external_packages = find_external_packages(prefix)
    if not external_packages:
        print(f"{OK_MARK} No external packages found.\n")
    else:
        print(f"{X_MARK} These packages are not installed by conda:\n")
        for package in external_packages:
            print(package.name)
        print("")


FORBIDDEN_LIST = {"msgpack", "ruamel-yaml", "pip", "setuptools"}


def conda_has_package(name: str) -> bool:
    result = subprocess.run(
        ["conda", "search", name, "--json"],
        capture_output=True,
        text=True,
    )
    return "error" not in result.stdout and result.returncode == 0


def build_migration_plan(packages):
    safe = []
    external_only = []

    for pkg in packages:
        name = pkg.name.replace("_", "-")

        # Do not migrate critical packages
        if name in FORBIDDEN_LIST:
            print(f"Skipping critical package: {name}")
            continue

        # check if conda can install it
        if conda_has_package(name):
            safe.append(name)
        else:
            external_only.append(name)

    return safe, external_only


def execute_migration(prefix, args, confirm, safe_packages):
    if not safe_packages:
        print("No safe packages to migrate.")
        return 0

    print(f"Found {len(safe_packages)} package(s) safe to migrate:")
    for name in sorted(safe_packages):
        print(f"  {name}")

    print()
    confirm("Reinstall these packages with conda?")

    successful_uninstalls = []

    # uninstall ONLY safe packages
    for name in safe_packages:
        print(f"Uninstalling {name} with pip...")

        result = subprocess.run(
            [sys.executable, "-m", "pip", "uninstall", "-y", name], check=False
        )

        if result.returncode != 0:
            print(f"Failed to uninstall {name} using `pip`.")
            continue

        successful_uninstalls.append(name)

    if not successful_uninstalls:
        print("No packages were successfully uninstalled. Aborting reinstall.")
        return 0

    return reinstall_packages(args, successful_uninstalls, force_reinstall=True)


def migrate_to_pypi(prefix: str, args: Namespace, confirm: ConfirmCallback) -> int:
    external_packages = find_external_packages(prefix)

    if not external_packages:
        print("No external packages found.")
        return 0

    safe, external_only = build_migration_plan(external_packages)

    return execute_migration(prefix, args, confirm, safe)


@hookimpl
def conda_health_checks() -> Iterable[CondaHealthCheck]:
    yield CondaHealthCheck(
        name="external-packages",
        action=print_external_packages,
        fixer=migrate_to_pypi,
        summary="List packages not installed by conda.",
    )
