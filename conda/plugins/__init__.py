# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import pluggy

from typing import Callable, NamedTuple, Optional
from collections.abc import Iterable


_hookspec = pluggy.HookspecMarker("conda")
register = pluggy.HookimplMarker("conda")


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
        [list[str]],  # arguments
        Optional[int],  # return code
    ]


@_hookspec
def conda_subcommands() -> Iterable[CondaSubcommand]:
    """
    Register external subcommands in conda.

    :return: An iterable of subcommand entries.
    """
