# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Fix task: Resolve missing or inconsistent dependencies."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .....base.context import context
from .....cli.helpers import add_output_and_prompt_options, add_parser_prefix
from .....core.prefix_data import PrefixData
from .....reporters import confirm_yn
from .... import hookimpl
from ....types import CondaHealthFix
from ...doctor.health_checks import find_inconsistent_packages

if TYPE_CHECKING:
    from argparse import ArgumentParser, Namespace

SUMMARY = "Resolve missing or inconsistent dependencies"


def configure_parser(parser: ArgumentParser) -> None:
    """Configure parser for inconsistent-packages fix task."""
    parser.description = (
        "Resolve missing or inconsistent package dependencies.\n\n"
        "This fix task identifies packages with missing or inconsistent "
        "dependencies (as reported by `conda doctor`) and attempts to "
        "resolve them by updating the environment."
    )
    add_parser_prefix(parser)
    add_output_and_prompt_options(parser)


def execute(args: Namespace) -> int:
    """Execute the inconsistent-packages fix task."""
    prefix_data = PrefixData.from_context()
    prefix_data.assert_environment()

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
    confirm_yn(
        "Attempt to resolve these dependency issues?",
        default="no",
        dry_run=context.dry_run,
    )

    # Install missing dependencies and update inconsistent ones
    from . import reinstall_packages

    specs = list(missing_deps) if missing_deps else []

    # Also add packages with inconsistent deps to trigger solver
    for pkg_name in issues:
        if pkg_name not in specs:
            specs.append(pkg_name)

    return reinstall_packages(args, specs, update_deps=True)


@hookimpl
def conda_health_fixes():
    """Register the inconsistent-packages fix."""
    yield CondaHealthFix(
        name="inconsistent-packages",
        summary=SUMMARY,
        configure_parser=configure_parser,
        execute=execute,
    )
