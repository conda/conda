# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Implementation for `conda plugins` subcommand."""

from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING

from ... import hookimpl
from ...types import CondaSubcommand
from . import info, install, list, remove, update

if TYPE_CHECKING:
    from argparse import ArgumentParser, Namespace


SUMMARY = "Manage conda plugins."


def configure_parser(parser: ArgumentParser) -> None:
    subparsers = parser.add_subparsers(
        title="subcommands",
        dest="subcommand",
    )

    info.configure_parser(subparsers.add_parser("info", help=info.HELP))
    install.configure_parser(subparsers.add_parser("install", help=install.HELP))
    list.configure_parser(subparsers.add_parser("list", help=list.HELP))
    remove.configure_parser(subparsers.add_parser("remove", help=remove.HELP))
    update.configure_parser(subparsers.add_parser("update", help=update.HELP))
    parser.set_defaults(func=partial(parser.parse_args, ["--help"]))


def execute(args: Namespace) -> int:
    return args.func(args)


@hookimpl
def conda_subcommands():
    yield CondaSubcommand(
        name="plugins",
        summary=SUMMARY,
        action=execute,
        configure_parser=configure_parser,
    )
