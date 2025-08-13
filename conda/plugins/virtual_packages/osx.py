# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Detect whether this is macOS."""

import os

from ...base.context import context
from .. import hookimpl
from ..types import CondaVirtualPackage


@hookimpl
def conda_virtual_packages():
    if not context.subdir.startswith("osx-"):
        return

    # 1: __osx (always exported if the target subdir is osx-*)
    yield CondaVirtualPackage("unix", None, None)

    # 2: __osx
    dist_version = os.getenv("CONDA_OVERRIDE_OSX")
    if dist_version is None:  # no override found, let's detect it
        dist_name, dist_version = context.os_distribution_name_version
        if dist_name != "OSX":
            # avoid reporting platform.version() of a different OS
            # this happens with CONDA_SUBDIR=osx-* in a non macOS machine
            dist_version = "0"
    if dist_version:  # truthy override found
        yield CondaVirtualPackage("osx", dist_version, None)
    # if a falsey override was found, the __osx virtual package is not exported
