# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import argparse

from ....base.context import context, locate_prefix_by_name
from ....cli.common import validate_prefix
from ....cli.conda_argparse import add_parser_prefix
from ....exceptions import CondaEnvException
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


def get_prefix(args: argparse.Namespace) -> str:
    """
    Determine the correct prefix to use provided the CLI arguments and the context object.

    When not specified via CLI options, the default is the currently active prefix
    """
    if args.name:
        return locate_prefix_by_name(args.name)

    if args.prefix:
        return validate_prefix(args.prefix)

    if context.active_prefix:
        return context.active_prefix

    raise CondaEnvException(
        "No environment specified. Activate an environment or specify the "
        "environment via `--name` or `--prefix`."
    )


def execute(argv: list[str]) -> None:
    """Run conda doctor subcommand."""
    from .health_checks import display_health_checks

    args = get_parsed_args(argv)
    prefix = get_prefix(args)
    display_health_checks(prefix, verbose=args.verbose)


@hookimpl
def conda_subcommands():
    yield CondaSubcommand(
        name="doctor",
        summary="A subcommand that displays environment health report",
        action=execute,
    )
