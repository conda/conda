# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Mock CLI implementation for `conda activate`.

A mock implementation of the activate shell command for better UX.
"""

from __future__ import annotations

from argparse import SUPPRESS
from typing import TYPE_CHECKING

from .. import CondaError

if TYPE_CHECKING:
    from argparse import ArgumentParser, Namespace, _SubParsersAction


def configure_parser(sub_parsers: _SubParsersAction, **kwargs) -> ArgumentParser:
    p = sub_parsers.add_parser(
        "activate",
        help="Activate a conda environment.",
        **kwargs,
    )
    p.set_defaults(func="conda.cli.main_mock_activate.execute")
    p.add_argument("args", action="store", nargs="*", help=SUPPRESS)

    return p


def execute(args: Namespace, parser: ArgumentParser) -> int:
    raise CondaError("Run 'conda init' before 'conda activate'")
