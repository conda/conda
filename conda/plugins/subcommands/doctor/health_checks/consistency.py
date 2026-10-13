# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Health check: Environment consistency (dependencies)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .....base.constants import OK_MARK, X_MARK
from .....base.context import context
from .....cli.install import reinstall_packages
from .....common.serialize import yaml
from .....core.prefix_data import PrefixData
from .....models.match_spec import MatchSpec
from .... import hookimpl
from ....types import CondaHealthCheck

if TYPE_CHECKING:
    from argparse import Namespace
    from collections.abc import Iterable

    from ....types import ConfirmCallback


def find_inconsistent_packages(
    prefix_data: PrefixData,
) -> tuple[dict[str, dict[str, list]], set[str]]:
    """Find packages with missing or inconsistent dependencies.

    Returns a tuple of (issues dict, missing dependency names set).
    The issues dict maps package name -> {"missing": [...], "inconsistent": [...]}.
    """
    pm = context.plugin_manager
    virtual_packages = {
        record.name: record for record in pm.get_virtual_package_records()
    }

    issues = {}
    missing_deps = set()

    for record in prefix_data.iter_records():
        for dependency in record.depends:
            match_spec = MatchSpec(dependency)
            dep_record = prefix_data.get(
                match_spec.name, default=virtual_packages.get(match_spec.name)
            )
            if dep_record is None:
                issues.setdefault(record.name, {}).setdefault("missing", []).append(
                    str(match_spec)
                )
                missing_deps.add(match_spec.name)
            elif not match_spec.match(dep_record):
                issues.setdefault(record.name, {}).setdefault(
                    "inconsistent", []
                ).append({"expected": str(match_spec), "installed": str(dep_record)})

        for constrain in record.constrains:
            package_found = prefix_data.get(
                MatchSpec(constrain).name,
                default=virtual_packages.get(MatchSpec(constrain).name),
            )
            if package_found is not None and not MatchSpec(constrain).match(
                package_found
            ):
                issues.setdefault(record.name, {}).setdefault(
                    "inconsistent", []
                ).append(
                    {
                        "expected": str(MatchSpec(constrain)),
                        "installed": f"{package_found.name}[version='{package_found.version}']",
                    }
                )

    return issues, missing_deps


def consistent_env_check(prefix: str, verbose: bool) -> None:
    """Health check action: Check environment consistency."""
    pd = PrefixData(prefix)
    issues, _ = find_inconsistent_packages(pd)

    if issues:
        print(f"{X_MARK} The environment is not consistent.\n")
        if verbose:
            print(yaml.dumps(issues))
    else:
        print(f"{OK_MARK} The environment is consistent.\n")


def fix_inconsistent_packages(
    prefix: str, args: Namespace, confirm: ConfirmCallback
) -> int:
    """Fix inconsistent packages by updating the environment."""
    prefix_data = PrefixData(prefix)
    issues, missing_deps = find_inconsistent_packages(prefix_data)

    if not issues:
        print("No inconsistent packages found.")
        return 0

    print(f"Found {len(issues)} package(s) with dependency issues:")
    for pkg_name, pkg_issues in sorted(issues.items()):
        missing = pkg_issues.get("missing", [])
        inconsistent = pkg_issues.get("inconsistent", [])
        print(f"  {pkg_name}:", end="")
        if missing:
            print(f" {len(missing)} missing", end="")
        if inconsistent:
            print(f" {len(inconsistent)} inconsistent", end="")
        print()

    print()
    confirm("Attempt to resolve these dependency issues?")

    # Install missing dependencies and update inconsistent ones
    specs = list(missing_deps) if missing_deps else []

    # Also add packages with inconsistent deps to trigger solver
    for pkg_name in issues:
        if pkg_name not in specs:
            specs.append(pkg_name)

    return reinstall_packages(args, specs, update_deps=True)


@hookimpl
def conda_health_checks() -> Iterable[CondaHealthCheck]:
    """Register the consistency health check."""
    yield CondaHealthCheck(
        name="consistency",
        action=consistent_env_check,
        fixer=fix_inconsistent_packages,
        summary="Check for missing or inconsistent dependencies",
        fix="Install missing dependencies",
    )
