# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations
from typing import TYPE_CHECKING

from .....auxlib.ish import dals
from ....argparse import ArgumentParser
from .list._parser import configure_parser as configure_parser_list
from .set._parser import configure_parser as configure_parser_set
from .unset._parser import configure_parser as configure_parser_unset

if TYPE_CHECKING:
    from argparse import _SubParsersAction


def configure_parser(
    parent: _SubParsersAction | None = None, name: str = "vars"
) -> ArgumentParser:
    help_ = description = "Interact with environment variables associated with Conda environments"
    epilog = dals(
        """
        examples:
            conda env config vars list -n my_env
            conda env config vars set MY_VAR=something OTHER_THING=ohhhhya
            conda env config vars unset MY_VAR
        """
    )

    # when a parent parser is specified add this as a subparser, otherwise create a new parser
    if parent:
        parser = parent.add_parser(name, help=help_, description=description, epilog=epilog)
    else:
        parser = ArgumentParser(name, description=description, epilog=epilog)

    # add options
    subparsers = parser.add_subparsers()
    configure_parser_list(subparsers)
    configure_parser_set(subparsers)
    configure_parser_unset(subparsers)

    # set executable for this scope
    parser.set_defaults(func="conda.cli.env.config.vars.__main__.execute")

    return parser
