# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""CLI implementation for `conda doctor`."""
from __future__ import annotations

import argparse
from argparse import _StoreTrueAction

from ....base.context import context
from ....cli.conda_argparse import (
    ArgumentParser,
    add_parser_details,
    add_parser_help,
    add_parser_prefix,
)
from ....deprecations import deprecated
from ... import CondaSubcommand, hookimpl


@deprecated(
    "24.3", "24.9", addendum="Use `conda.base.context.context.target_prefix` instead."
)
def get_prefix(args: argparse.Namespace) -> str:
    context.__init__(argparse_args=args)
    return context.target_prefix


def configure_parser(parser: ArgumentParser):
    parser.add_argument(
        "-v",
        "--verbose",
        dest="details",
        action=deprecated.action(
            "24.3",
            "24.9",
            _StoreTrueAction,
            addendum="Use `--details` instead.",
        ),
    )
    add_parser_details(parser, "Generate a detailed environment health report.")
    add_parser_help(parser)
    add_parser_prefix(parser)


def execute(args: argparse.Namespace) -> None:
    """Run conda doctor subcommand."""
    from .health_checks import display_health_checks

    display_health_checks(context.target_prefix, details=args.details)


@hookimpl
def conda_subcommands():
    yield CondaSubcommand(
        name="doctor",
        summary="Display a health report for your environment.",
        action=execute,
        configure_parser=configure_parser,
    )
