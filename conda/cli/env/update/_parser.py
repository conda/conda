# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations
from typing import TYPE_CHECKING

from ....auxlib.ish import dals
from ...argparse import ArgumentParser
from ...helpers import add_parser_prefix, add_parser_json, add_parser_experimental_solver

if TYPE_CHECKING:
    from argparse import _SubParsersAction


def configure_parser(
    parent: _SubParsersAction | None = None, name: str = "vars"
) -> ArgumentParser:
    help_ = description = "Update the current environment based on environment file"
    epilog = dals(
        """
        examples:
            conda env update
            conda env update -n=foo
            conda env update -f=/path/to/environment.yml
            conda env update --name=foo --file=environment.yml
            conda env update vader/deathstar
        """
    )

    # when a parent parser is specified add this as a subparser, otherwise create a new parser
    if parent:
        parser = parent.add_parser(name, help=help_, description=description, epilog=epilog)
    else:
        parser = ArgumentParser(name, description=description, epilog=epilog)

    # add options
    add_parser_prefix(parser)
    parser.add_argument(
        "-f",
        "--file",
        action="store",
        help="environment definition (default: environment.yml)",
        default="environment.yml",
    )
    parser.add_argument(
        "--prune",
        action="store_true",
        default=False,
        help="remove installed packages not defined in environment.yml",
    )
    parser.add_argument(
        "remote_definition",
        help="remote environment definition / IPython notebook",
        action="store",
        default=None,
        nargs="?",
    )
    add_parser_json(parser)
    add_parser_experimental_solver(parser)

    # set executable for this scope
    parser.set_defaults(func="conda.cli.env.update.__main__.execute")

    return parser
