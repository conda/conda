# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import argparse

from ....base.context import context, determine_target_prefix
from ....cli.conda_argparse import add_parser_prefix
from ....deprecations import deprecated
from ... import CondaSubcommand, hookimpl


def get_parsed_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        "conda doctor",
        description="Display a health report for your environment.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="generate a detailed environment health report",
    )
    add_parser_prefix(parser)
    args = parser.parse_args(argv)

    return args


@deprecated(
    "24.3",
    "24.9",
    addendum="Use `conda.base.context.determine_target_prefix` instead.",
)
def get_prefix(args: argparse.Namespace) -> str:
    return determine_target_prefix(context, args)


def execute(argv: list[str]) -> None:
    """Run conda doctor subcommand."""
    from .health_checks import display_health_checks

    args = get_parsed_args(argv)
    prefix = determine_target_prefix(context, args)
    display_health_checks(prefix, verbose=args.verbose)


@hookimpl
def conda_subcommands():
    yield CondaSubcommand(
        name="doctor",
        summary="A subcommand that displays environment health report",
        action=execute,
    )
