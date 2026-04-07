# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Mock CLI implementation for `conda activate`.

A mock implementation of the activate shell command for better UX.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from argparse import ArgumentParser, Namespace, _SubParsersAction


def configure_parser(sub_parsers: _SubParsersAction, **kwargs) -> ArgumentParser:
    p = sub_parsers.add_parser(
        "commands",
        help=(
            "List all available conda subcommands (including those from plugins). "
            "Generally only used by tab-completion."
        ),
        **kwargs,
    )
    p.set_defaults(func="conda.cli.main_commands.execute")

    return p


def execute(args: Namespace, parser: ArgumentParser) -> int:
    from .conda_argparse import find_builtin_commands

    # Ensure plugin subcommands are discovered before listing
    sub_parsers_action = parser._subparsers._group_actions[0]
    if hasattr(sub_parsers_action, "_ensure_plugins_loaded"):
        sub_parsers_action._ensure_plugins_loaded()

    print(
        *sorted(find_builtin_commands(parser)),
        sep="\n",
        end="",
    )
    return 0
