# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Implementation for `conda fix` subcommand.

Provides a framework for health fixes that help users diagnose and repair
issues in their conda setup.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ....base.context import context
from ....cli.common import stdout_json
from ....cli.helpers import add_output_and_prompt_options
from ... import hookimpl
from ...types import CondaSubcommand

if TYPE_CHECKING:
    from argparse import ArgumentParser, Namespace


def configure_parser(parser: ArgumentParser) -> None:
    parser.description = (
        "Apply health fixes for conda environments and configuration.\n\n"
        "The fix command helps you diagnose and repair issues in your conda setup. "
        "Each health fix addresses a specific problem or improves your conda workflow.\n\n"
        "Use `conda fix --list` to see available health fixes."
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all available health fixes",
    )
    add_output_and_prompt_options(parser)

    subparsers = parser.add_subparsers(
        title="health fixes",
        dest="fix_name",
    )

    # Register subparsers for each health fix from plugins
    for name, fix in context.plugin_manager.get_health_fixes().items():
        fix_parser = subparsers.add_parser(name, help=fix.summary)
        fix.configure_parser(fix_parser)
        fix_parser.set_defaults(fix=fix)


def execute(args: Namespace) -> int:
    """Run the specified health fix or list available health fixes."""
    if args.list:
        health_fixes = context.plugin_manager.get_health_fixes()
        if context.json:
            stdout_json(
                [{"name": name, "summary": fix.summary} for name, fix in health_fixes.items()]
            )
        else:
            print("Available health fixes:\n")
            for name, fix in sorted(health_fixes.items()):
                print(f"  {name:<24}  {fix.summary}")
        return 0

    # If no health fix was provided, show error
    if not hasattr(args, "fix"):
        from ....exceptions import CondaError

        raise CondaError("No health fix specified. Use `conda fix --list` to see available health fixes.")

    return args.fix.execute(args)


@hookimpl
def conda_subcommands():
    yield CondaSubcommand(
        name="fix",
        summary="Apply health fixes for conda environments and configuration.",
        action=execute,
        configure_parser=configure_parser,
    )
