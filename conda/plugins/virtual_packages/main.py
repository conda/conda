# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from itertools import chain
from typing import Iterable

import pluggy

from .specs import archspec, cuda, linux, osx, windows
from ..hooks import CondaVirtualPackage


def register(pm: pluggy.PluginManager) -> None:
    """
    Please add a nice doc string too explaining why this function exists!
    """
    pm.register(archspec)
    pm.register(cuda)
    pm.register(linux)
    pm.register(osx)
    pm.register(windows)


def find_virtual_package(
    plugin_manager: pluggy.PluginManager, search: str
) -> CondaVirtualPackage | None:
    """
    Given a search string and a plugin manager, first grab all the registered
    CondaVirtualPacakge objects and then search through them for the correct one.

    Return `None` means we were not able to find anything
    """
    conda_virtual_packages: list[
        Iterable[CondaVirtualPackage]
    ] = plugin_manager.hook.conda_virtual_packages()

    # Find the virtual package
    try:
        virtual_package, *_ = tuple(
            package for package in chain(*conda_virtual_packages) if package.name == search
        )
    except ValueError:
        # This means that we were not able to find any results
        return

    return virtual_package
