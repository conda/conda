# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Mock CLI implementation for `conda activate`.

A mock implementation of the activate shell command for better UX.
"""
from argparse import SUPPRESS

from conda import CondaError


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        "activate",
        help="Activate a conda environment.",
    )
    p.set_defaults(func="conda.cli.command.main_mock_activate.execute")
    p.add_argument("args", action="store", nargs="*", help=SUPPRESS)


def execute(args, parser):
    raise CondaError("Run 'conda init' before 'conda activate'")
