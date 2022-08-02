# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import pluggy
import sys

from typing import Callable, NamedTuple


if sys.version_info < (3, 9):
    from typing import Iterable
else:
    from collections.abc import Iterable


_hookspec = pluggy.HookspecMarker("conda")
register = pluggy.HookimplMarker("conda")


class CondaSubcommand(NamedTuple):
    """
    Conda subcommand entry.

    :param name: Subcommand name (e.g., ``conda my-subcommand-name``).
    :param summary: Subcommand summary, will be shown in ``conda --help``.
    :param add_argument_parser: Function that adds the parser to the main conda argument parser
    """
    name: str
    summary: str
    add_argument_parser: Callable


@_hookspec
def conda_subcommands() -> Iterable[CondaSubcommand]:
    """
    Register external subcommands in conda.

    :return: An iterable of subcommand entries.
    """
