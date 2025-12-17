# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Implementation for `conda fix` subcommand.

Provides a framework for fix tasks that help users diagnose and repair
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
        "Apply fixes for conda environments and configuration.\n\n"
        "The fix command helps you diagnose and repair issues in your conda setup. "
        "Each fix task addresses a specific problem or improves your conda workflow.\n\n"
        "Use `conda fix --list` to see available fix tasks."
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all available fix tasks",
    )
    add_output_and_prompt_options(parser)

    subparsers = parser.add_subparsers(
        title="fix tasks",
        dest="task",
    )

    # Register subparsers for each fix task from plugins
    for name, task in context.plugin_manager.get_fix_tasks().items():
        task_parser = subparsers.add_parser(name, help=task.summary)
        task.configure_parser(task_parser)
        task_parser.set_defaults(fix_task=task)


def execute(args: Namespace) -> int:
    """Run the specified fix task or list available tasks."""
    if args.list:
        tasks = context.plugin_manager.get_fix_tasks()
        if context.json:
            stdout_json(
                [{"name": name, "summary": task.summary} for name, task in tasks.items()]
            )
        else:
            print("Available fix tasks:\n")
            for name, task in sorted(tasks.items()):
                print(f"  {name:<12}  {task.summary}")
        return 0

    # If no task was provided, show error
    if not hasattr(args, "fix_task"):
        from ....exceptions import CondaError

        raise CondaError("No fix task specified. Use `conda fix --list` to see available tasks.")

    return args.fix_task.execute(args)


@hookimpl
def conda_subcommands():
    yield CondaSubcommand(
        name="fix",
        summary="Apply fixes for conda environments and configuration.",
        action=execute,
        configure_parser=configure_parser,
    )
