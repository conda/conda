# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Implementation for `conda doctor` subcommand.
Adds various environment and package checks to detect issues or possible environment
corruption.
"""

from __future__ import annotations

import argparse

from ....base.context import context
from ....cli.conda_argparse import (
    ArgumentParser,
    add_parser_help,
    add_parser_prefix,
    add_parser_verbose,
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
    add_parser_verbose(parser)
    add_parser_help(parser)
    add_parser_prefix(parser)


def execute(args: argparse.Namespace) -> None:
    """Run conda doctor subcommand."""
    from .health_checks import display_health_checks

    display_health_checks(context.target_prefix, verbose=context.verbose)


@hookimpl
def conda_subcommands():
    yield CondaSubcommand(
        name="doctor",
        summary="Display a health report for your environment.",
        action=execute,
        configure_parser=configure_parser,
    )
