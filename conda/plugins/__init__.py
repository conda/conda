# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

import pluggy
import sys

from typing import Callable, List, NamedTuple, Optional


if sys.version_info < (3, 9):
    from typing import Iterable
else:
    from collections.abc import Iterable


_hookspec = pluggy.HookspecMarker('conda')
hookimp = pluggy.HookimplMarker('conda')


class CondaSubcommand(NamedTuple):
    """
    Conda subcommand entry.

    :param name: Subcommand name (e.g., ``conda my-subcommand-name``).
    :param summary: Subcommand summary, will be shown in ``conda --help``.
    :param action: Callable that will be run when the subcommand is invoked.
    """
    name: str
    summary: str
    action: Callable[
        [List[str]],  # arguments
        Optional[int],  # return code
    ]


@_hookspec
def conda_cli_register_subcommands() -> Iterable[CondaSubcommand]:
    """
    Register external subcommands in conda.

    :return: An iterable of subcommand entries.
    """
