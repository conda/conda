# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import argparse
from . import health_checks

from ... import CondaSubcommand, hookimpl
from ....base.context import context


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
    args = parser.parse_args(argv)

    return args


def display_health_checks(args: argparse.Namespace) -> None:
    if args.verbose:
        health_checks.run_detailed_health_checks(context)
    else:
        health_checks.run_health_checks(context)


def execute(argv: list[str]) -> int:
    args = get_parsed_args(argv)
    display_health_checks(args)

@hookimpl
def conda_subcommands():
    yield CondaSubcommand(
        name="doctor",
        summary="A subcommand that displays environment health report",
        action=execute,
    )
