# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import argparse
from pathlib import Path

from ... import CondaSubcommand, hookimpl
from ....cli.conda_argparse import add_parser_prefix
from ....base.context import locate_prefix_by_name, context
from ....exceptions import CondaError

from . import health_checks


def get_parsed_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        "conda doctor", description="Display a health report for your environment."
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


def validate_prefix(prefix: str) -> str:
    """
    Make sure that the prefix is an existing folder

    :raises CondaError: When the prefix does not point to existing folder
    """
    prefix_path = Path(prefix)

    if not prefix_path.is_dir():
        raise CondaError("Provided prefix does not exist.")

    return prefix


def get_prefix(args: argparse.Namespace) -> str:
    """
    Determine the correct prefix to use provided the CLI arguments and the context object.

    When not specified via CLI options, the default is the currently active prefix
    """
    if args.name:
        return locate_prefix_by_name(args.name)

    if args.prefix:
        return validate_prefix(args.prefix)

    return context.active_prefix


def display_health_checks(prefix: str, verbose: bool = False) -> None:
    """
    TODO: docstring
    """
    if verbose:
        health_checks.display_detailed_health_checks(prefix)
    else:
        health_checks.display_health_checks(prefix)


def execute(argv: list[str]) -> None:
    """
    TODO: docstring
    """
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
