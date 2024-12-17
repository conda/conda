# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Detect whether this is macOS."""

import os

from ...base.context import context
from .. import CondaVirtualPackage, hookimpl


@hookimpl
def conda_virtual_packages():
    if not context.subdir.startswith("osx-"):
        return

    yield CondaVirtualPackage("unix", None, None)

    dist_version = os.environ.get("CONDA_OVERRIDE_OSX")
    if dist_version is None:
        dist_name, dist_version = context.os_distribution_name_version
        if dist_name != "OSX":
            # avoid reporting platform.version() of other OS
            # this happens with CONDA_SUBDIR=osx-* in a non macOS machine
            dist_version = "0"
    if dist_version:
        yield CondaVirtualPackage("osx", dist_version, None)
