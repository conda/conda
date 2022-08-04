# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import sys
from functools import lru_cache
from typing import Callable, NamedTuple, Optional, Iterable

import pluggy

from ..auxlib.ish import dals
from ..base import context
from .. import CondaError
from ..common.io import dashlist

_hookspec = pluggy.HookspecMarker("conda")
register = pluggy.HookimplMarker("conda")


class PluginError(CondaError):
    pass


class CondaSubcommand(NamedTuple):
    """
    Conda subcommand entry.
    """

    name: str
    "Subcommand name (e.g., ``conda my-subcommand-name``)."

    summary: str
    "Subcommand summary, will be shown in ``conda --help``."

    action: Callable
    "Function that is called when subcommand is to be invoked"


@_hookspec
def conda_subcommands() -> Iterable[CondaSubcommand]:
    """
    Register external subcommands in conda.

    :return: An iterable of subcommand entries.
    """


def get_plugin_subcommands():
    """
    We use this function as a way to retrieve all of our register plugin subcommands.

    It will raise an exception if duplicate plugin subcommands are found.
    """
    pm = context.get_plugin_manager()

    subcommands = sorted(
        (subcommand for subcommands in pm.hook.conda_subcommands() for subcommand in subcommands),
        key=lambda subcommand: subcommand.name,
    )

    # Check for conflicts
    seen = set()
    conflicts = [
        subcommand
        for subcommand in subcommands
        if subcommand.name in seen or seen.add(subcommand.name)
    ]
    if conflicts:
        raise PluginError(
            dals(
                f"""
                Conflicting entries found for the following subcommands:
                {dashlist(conflicts)}
                Multiple conda plugins are registering these subcommands via the
                `conda_subcommands` hook; please make sure that
                you do not have any incompatible plugins installed.
                """
            )
        )

    return subcommands


def find_plugin_subcommand(name: str) -> Optional[CondaSubcommand]:
    """
    We use this to find an individual subcommand by name
    """
    plugin_subcommands = get_plugin_subcommands()

    filtered_set = tuple(
        subcommand for subcommand in plugin_subcommands if subcommand.name == name
    )

    if len(filtered_set) > 0:
        return filtered_set[0]


@lru_cache(1)
def is_plugin_subcommand() -> bool:
    """Determines if the running process is a plugin subcommand or not"""
    if len(sys.argv) > 1:
        name = sys.argv[1]
        return find_plugin_subcommand(name) is not None
    else:
        return False
