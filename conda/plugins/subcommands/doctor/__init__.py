# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Implementation for `conda doctor` subcommand.
Adds various environment and package checks to detect issues or possible environment
corruption.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ....base.context import context
from ....cli.helpers import (
    add_parser_help,
    add_parser_prefix,
    add_parser_verbose,
)
from ....core.prefix_data import PrefixData
from ... import hookimpl
from ...types import CondaSubcommand

if TYPE_CHECKING:
    from argparse import ArgumentParser, Namespace


def configure_parser(parser: ArgumentParser):
    add_parser_help(parser)
    add_parser_prefix(parser)
    add_parser_verbose(parser)
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all available health checks and their fix capabilities.",
    )
    parser.add_argument(
        "--fix",
        nargs="*",
        metavar="ID",
        help=(
            "Fix issues found by health checks. "
            "Optionally specify which checks to fix by id (e.g., --fix missing-files)."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only display what would have been done without actually fixing.",
    )
    parser.add_argument(
        "-y",
        "--yes",
        action="store_true",
        help="Do not ask for confirmation.",
    )


def execute(args: Namespace) -> int:
    """Run registered health_check plugins and optionally fix issues."""
    # Handle --list first (doesn't require environment)
    if getattr(args, "list", False):
        checks = context.plugin_manager.get_health_checks()
        if not checks:
            print("No health checks are available.")
            return 0

        print("Available health checks:\n")
        for id, check in sorted(checks.items()):
            fix_marker = " [fixable]" if check.fix else ""
            summary = check.summary or check.name
            print(f"  {id}: {summary}{fix_marker}")
        print()
        return 0

    prefix_data = PrefixData.from_context()
    prefix_data.assert_environment()
    prefix = str(prefix_data.prefix_path)

    # Always run health checks first
    print(f"Environment Health Report for: {prefix}\n")
    context.plugin_manager.invoke_health_checks(prefix, context.verbose)

    # If --fix was provided, run fixes
    if args.fix is not None:
        print("\n" + "=" * 60)
        print("Running fixes...")
        print("=" * 60 + "\n")

        # Get list of check ids to fix (empty list means all)
        check_ids = args.fix if args.fix else None

        # Show available fixable checks if none specified
        fixable = context.plugin_manager.get_fixable_health_checks()
        if not fixable:
            print("No health checks with fix capability are available.")
            return 0

        if check_ids is None:
            print("Available fixes:")
            for id, check in sorted(fixable.items()):
                summary = check.summary or check.name
                print(f"  {id}: {summary}")
            print()

        return context.plugin_manager.invoke_health_fixes(prefix, args, check_ids)

    return 0


@hookimpl
def conda_subcommands():
    yield CondaSubcommand(
        name="doctor",
        summary="Display a health report for your environment.",
        action=execute,
        configure_parser=configure_parser,
    )
    yield CondaSubcommand(
        name="check",
        summary="Display a health report for your environment (alias for doctor).",
        action=execute,
        configure_parser=configure_parser,
    )
