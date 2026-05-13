# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""CLI implementation for `conda create` — env-setup preview stub.

This module is part of the ``env-setup`` preview feature. It intercepts
``conda create`` when the preview is enabled and raises ``OperationNotAllowed``
until a functional implementation is available.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ....base.context import context
from ....cli.helpers import (
    add_output_and_prompt_options,
    add_parser_help,
    add_parser_prefix,
)
from ....exceptions import OperationNotAllowed
from ....plugins import hookimpl
from ....plugins.types import CondaSubcommand

if TYPE_CHECKING:
    from argparse import ArgumentParser, Namespace


def configure_parser(parser: ArgumentParser) -> None:
    add_parser_help(parser)
    add_parser_prefix(parser)
    add_output_and_prompt_options(parser)


def execute(args: Namespace) -> int:
    raise OperationNotAllowed(
        "The 'env-setup' preview implementation of 'conda create' is not yet available."
    )


@hookimpl
def conda_subcommands() -> None:
    if "env-setup" in context.preview:
        yield CondaSubcommand(
            name="create",
            summary="Create a new conda environment.",
            action=execute,
            configure_parser=configure_parser,
        )
