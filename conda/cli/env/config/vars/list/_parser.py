# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations
from typing import TYPE_CHECKING

from ......auxlib.ish import dals
from .....argparse import ArgumentParser
from .....helpers import add_parser_prefix, add_parser_json

if TYPE_CHECKING:
    from argparse import _SubParsersAction


def configure_parser(
    parent: _SubParsersAction | None = None, name: str = "list"
) -> ArgumentParser:
    help_ = description = "List environment variables for a conda environment"
    epilog = dals(
        """
        examples:
            conda env config vars list -n my_env
        """
    )

    # when a parent parser is specified add this as a subparser, otherwise create a new parser
    if parent:
        parser = parent.add_parser(name, help=help_, description=description, epilog=epilog)
    else:
        parser = ArgumentParser(name, description=description, epilog=epilog)

    # add options
    add_parser_prefix(parser)
    add_parser_json(parser)

    # set executable for this scope
    parser.set_defaults(func="conda.cli.env.config.vars.list.__main__.execute")

    return parser
