# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations
from typing import TYPE_CHECKING

from ..argparse import ArgumentParser
from .config._parser import configure_parser as configure_parser_config
from .create._parser import configure_parser as configure_parser_create
from .export._parser import configure_parser as configure_parser_export
from .list._parser import configure_parser as configure_parser_list
from .remove._parser import configure_parser as configure_parser_remove
from .update._parser import configure_parser as configure_parser_update

if TYPE_CHECKING:
    from argparse import _SubParsersAction


def configure_parser(parent: _SubParsersAction | None = None, name: str = "env") -> ArgumentParser:
    help_ = description = ""
    epilog = ""

    # when a parent parser is specified add this as a subparser, otherwise create a new parser
    if parent:
        parser = parent.add_parser(name, help=help_, description=description, epilog=epilog)
    else:
        parser = ArgumentParser(name, description=description, epilog=epilog)

    # add options
    subparsers = parser.add_subparsers()
    configure_parser_create(subparsers)
    configure_parser_export(subparsers)
    configure_parser_list(subparsers)
    configure_parser_remove(subparsers)
    configure_parser_update(subparsers)
    configure_parser_config(subparsers)

    # set executable for this scope
    parser.set_defaults(func="conda.cli.env.__main__.execute")

    return parser
