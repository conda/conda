# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations
from typing import TYPE_CHECKING

from ....auxlib.ish import dals
from ...argparse import ArgumentParser
from ...helpers import add_parser_prefix, add_parser_json

if TYPE_CHECKING:
    from argparse import _SubParsersAction


def configure_parser(
    parent: _SubParsersAction | None = None, name: str = "export"
) -> ArgumentParser:
    help_ = description = "Export a given environment"
    epilog = dals(
        """
        examples:
            conda env export
            conda env export --file SOME_FILE
        """
    )

    # when a parent parser is specified add this as a subparser, otherwise create a new parser
    if parent:
        parser = parent.add_parser(name, help=help_, description=description, epilog=epilog)
    else:
        parser = ArgumentParser(name, description=description, epilog=epilog)

    # add options
    parser.add_argument(
        "-c", "--channel", action="append", help="Additional channel to include in the export"
    )
    parser.add_argument(
        "--override-channels",
        action="store_true",
        help="Do not include .condarc channels",
    )
    add_parser_prefix(parser)
    parser.add_argument("-f", "--file", default=None, required=False)
    parser.add_argument(
        "--no-builds",
        default=False,
        action="store_true",
        required=False,
        help="Remove build specification from dependencies",
    )
    parser.add_argument(
        "--ignore-channels",
        default=False,
        action="store_true",
        required=False,
        help="Do not include channel names with package names.",
    )
    add_parser_json(parser)
    parser.add_argument(
        "--from-history",
        default=False,
        action="store_true",
        required=False,
        help="Build environment spec from explicit specs in history",
    )

    # set executable for this scope
    parser.set_defaults(func=".main_export.execute")

    return parser
