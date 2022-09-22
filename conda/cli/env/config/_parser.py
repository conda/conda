# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations
from typing import TYPE_CHECKING

from ....auxlib.ish import dals
from ...argparse import ArgumentParser
from .vars._parser import configure_parser as configure_parser_vars

if TYPE_CHECKING:
    from argparse import _SubParsersAction


def configure_parser(
    parent: _SubParsersAction | None = None, name: str = "config"
) -> ArgumentParser:
    help_ = description = "Configure a conda environment"
    epilog = dals(
        """
        examples:
            conda env config vars list
            conda env config --append channels conda-forge
        """
    )

    # when a parent parser is specified add this as a subparser, otherwise create a new parser
    if parent:
        parser = parent.add_parser(name, help=help_, description=description, epilog=epilog)
    else:
        parser = ArgumentParser(name, description=description, epilog=epilog)

    # add options
    subparsers = parser.add_subparsers()
    configure_parser_vars(subparsers)

    # set executable for this scope
    parser.set_defaults(func=".env.config.__main__.execute")

    return parser
