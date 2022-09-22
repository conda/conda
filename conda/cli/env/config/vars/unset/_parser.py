# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations
from typing import TYPE_CHECKING

from ......auxlib.ish import dals
from .....argparse import ArgumentParser
from .....helpers import add_parser_prefix

if TYPE_CHECKING:
    from argparse import _SubParsersAction


def configure_parser(
    parent: _SubParsersAction | None = None, name: str = "vars"
) -> ArgumentParser:
    help_ = description = "Unset environment variables for a conda environment"
    epilog = dals(
        """
        example:
            conda env config vars unset MY_VAR
        """
    )

    # when a parent parser is specified add this as a subparser, otherwise create a new parser
    if parent:
        parser = parent.add_parser(name, help=help_, description=description, epilog=epilog)
    else:
        parser = ArgumentParser(name, description=description, epilog=epilog)

    # add options
    parser.add_argument(
        "vars",
        action="store",
        nargs="*",
        help="Environment variables to unset in the form <KEY> separated by spaces",
    )
    add_parser_prefix(parser)

    # set executable for this scope
    parser.set_defaults(func=".main_vars.execute_unset")

    return parser
