# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Mock CLI implementation for `conda deactivate`.

A mock implementation of the deactivate shell command for better UX.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .. import CondaError

if TYPE_CHECKING:
    from argparse import ArgumentParser, Namespace, _SubParsersAction


def configure_parser(sub_parsers: _SubParsersAction, **kwargs) -> ArgumentParser:
    from .conda_argparse import BUILTIN_SUBCOMMANDS

    p = sub_parsers.add_parser(
        "deactivate",
        help=BUILTIN_SUBCOMMANDS["deactivate"]["help"],
        **kwargs,
    )
    p.set_defaults(func="conda.cli.main_mock_deactivate.execute")

    return p


def execute(args: Namespace, parser: ArgumentParser) -> int:
    raise CondaError("Run 'conda init' before 'conda deactivate'")
