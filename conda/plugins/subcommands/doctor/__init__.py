# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Implementation for `conda doctor` subcommand.
Adds various environment and package checks to detect issues or possible environment
corruption.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ....base.context import context
from ....cli.helpers import (
    add_output_and_prompt_options,
    add_parser_help,
    add_parser_prefix,
)
from ....core.prefix_data import PrefixData
from ....exceptions import CondaSystemExit, DryRunExit
from ....reporters import confirm_yn
from ... import hookimpl
from ...types import CondaSubcommand

if TYPE_CHECKING:
    from argparse import ArgumentParser, Namespace

log = logging.getLogger(__name__)


def configure_parser(parser: ArgumentParser):
    add_parser_help(parser)
    add_parser_prefix(parser)
    add_output_and_prompt_options(parser)  # includes --verbose, --dry-run, --yes
    parser.add_argument(
        "checks",
        nargs="*",
        metavar="NAME",
        help="Health check names to run (default: all). Use --list to see available checks.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all available health checks and their fix capabilities.",
    )
    parser.add_argument(
        "--fix",
        "--heal",  # easter egg 🩺
        action="store_true",
        help="Fix issues found by health checks.",
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
        for name, check in sorted(checks.items()):
            summary = check.summary or name
            if check.fixer:
                fix = check.fix or "Fix available"
                print(f"  {name}: {summary} (fix: {fix})")
            else:
                print(f"  {name}: {summary}")
        print()
        return 0

    prefix_data = PrefixData.from_context()
    prefix_data.assert_environment()
    prefix = str(prefix_data.prefix_path)

    # Get and filter health checks by name
    checks = context.plugin_manager.get_health_checks()
    check_names = args.checks if args.checks else None
    if check_names:
        unknown = set(check_names) - set(checks.keys())
        if unknown:
            log.warning(f"Unknown health check(s): {', '.join(sorted(unknown))}")
        checks = {n: c for n, c in checks.items() if n in check_names}

    # Run health checks
    print(f"Environment Health Report for: {prefix}\n")
    for name, check in checks.items():
        try:
            check.action(prefix, context.verbose)
        except Exception as err:
            log.warning(f"Error running health check: {name} ({err})")

    # If --fix was provided, run fixes
    if getattr(args, "fix", False):
        print("\n" + "=" * 60)
        print("Running fixes...")
        print("=" * 60 + "\n")

        fixable = {n: c for n, c in checks.items() if c.fixer}
        if not fixable:
            print("No health checks with fix capability are available.")
            return 0

        exit_code = 0
        confirm = lambda msg: confirm_yn(msg, default="no", dry_run=context.dry_run)
        for name, check in fixable.items():
            try:
                result = check.fixer(prefix, args, confirm)
                if result != 0:
                    exit_code = result
            except DryRunExit as exc:
                # Dry-run mode: print the message and continue to next fixer
                log.warning(str(exc))
            except CondaSystemExit:
                # User cancelled the fix
                pass
            except Exception as err:
                log.warning(f"Error running fix: {name} ({err})")
                exit_code = 1
        return exit_code

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
