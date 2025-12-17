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
        "--fix",
        nargs="*",
        metavar="CHECK",
        help=(
            "Fix issues found by health checks. "
            "Optionally specify which checks to fix (e.g., --fix 'Missing Files')."
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

        # Get list of checks to fix (empty list means all)
        check_names = args.fix if args.fix else None

        # Show available fixable checks if none specified
        fixable = context.plugin_manager.get_fixable_health_checks()
        if not fixable:
            print("No health checks with fix capability are available.")
            return 0

        if check_names is None:
            print("Available fixes:")
            for name, check in sorted(fixable.items()):
                summary = check.summary or "No description"
                print(f"  {name}: {summary}")
            print()

        return context.plugin_manager.invoke_health_fixes(prefix, args, check_names)

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
