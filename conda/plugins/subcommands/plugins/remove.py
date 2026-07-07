# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Implementation for `conda plugins remove` subcommand."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ....cli import main_remove
from ....cli.helpers import (
    add_output_and_prompt_options,
    add_parser_channels,
    add_parser_frozen_env,
    add_parser_networking,
    add_parser_prefix,
    add_parser_prune,
    add_parser_pscheck,
    add_parser_solver,
)
from ....common.constants import NULL
from .package_validation import require_installed_plugin_specs

if TYPE_CHECKING:
    from argparse import ArgumentParser, Namespace


HELP = "Remove conda plugin packages from an environment."


def configure_parser(parser: ArgumentParser) -> None:
    parser.description = HELP
    add_parser_frozen_env(parser)
    add_parser_pscheck(parser)
    add_parser_prefix(parser)
    add_parser_channels(parser)

    solver_mode_options = parser.add_argument_group("Solver Mode Modifiers")
    solver_mode_options.add_argument(
        "--force-remove",
        "--force",
        action="store_true",
        help="Remove a plugin package without removing packages that depend on it. Using this option will usually leave your environment broken.",
        dest="force_remove",
    )
    solver_mode_options.add_argument(
        "--no-pin",
        action="store_true",
        dest="ignore_pinned",
        default=NULL,
        help="Ignore pinned package(s) that apply to the current operation.",
    )
    add_parser_prune(solver_mode_options)
    add_parser_solver(solver_mode_options)
    add_parser_networking(parser)
    add_output_and_prompt_options(parser)
    parser.add_argument(
        "package_names",
        metavar="package_name",
        action="store",
        nargs="*",
        help="Plugin package names to remove from the environment.",
    )
    parser.set_defaults(
        func=execute,
        _plugin_parser=parser,
        all=False,
        features=False,
        keep_env=False,
    )


def execute(args: Namespace) -> int:
    require_installed_plugin_specs(args.package_names, "remove")
    args.cmd = "remove"
    return main_remove.execute(args, args._plugin_parser)
