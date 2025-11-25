# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Implementation for `conda doctor` subcommand.
Adds various environment and package checks to detect issues or possible environment
corruption.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ....base.context import context
from ....cli.helpers import (
    add_parser_help,
    add_parser_prefix,
    add_parser_verbose,
)
from ....core.prefix_data import PrefixData
from ... import hookimpl
from ...types import CondaSubcommand

if TYPE_CHECKING:
    from argparse import ArgumentParser, Namespace


def configure_parser(parser: ArgumentParser):
    add_parser_verbose(parser)
    add_parser_help(parser)
    add_parser_prefix(parser)


def execute(args: Namespace) -> None:
    """Run registered health_check plugins."""
    prefix_data = PrefixData.from_context()
    prefix_data.assert_environment()
    prefix = str(prefix_data.prefix_path)
    print(f"Environment Health Report for: {prefix}\n")
    context.plugin_manager.invoke_health_checks(prefix, context.verbose)


@hookimpl
def conda_subcommands():
    yield CondaSubcommand(
        name="doctor",
        summary="Display a health report for your environment.",
        action=execute,
        configure_parser=configure_parser,
    )
