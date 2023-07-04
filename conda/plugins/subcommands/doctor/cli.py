# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""CLI implementation for `conda doctor`."""
from __future__ import annotations

import argparse

from ....base.context import context
from ....cli.conda_argparse import add_parser_prefix
from ....deprecations import deprecated
from ... import CondaSubcommand, hookimpl


def generate_parser() -> argparse.ArgumentParser:
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
    return parser


def get_parsed_args(argv: list[str]) -> argparse.Namespace:
    parser = generate_parser()
    return parser.parse_args(argv)


@deprecated(
    "24.3", "24.9", addendum="Use `conda.base.context.context.target_prefix` instead."
)
def get_prefix(args: argparse.Namespace) -> str:
    context.__init__(argparse_args=args)
    return context.target_prefix


def execute(argv: list[str]) -> None:
    """Run conda doctor subcommand."""
    from .health_checks import display_health_checks

    args = get_parsed_args(argv)
    context.__init__(argparse_args=args)
    display_health_checks(context.target_prefix, verbose=args.verbose)


@hookimpl
def conda_subcommands():
    yield CondaSubcommand(
        name="doctor",
        summary="A subcommand that displays environment health report",
        action=execute,
    )
