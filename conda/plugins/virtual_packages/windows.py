# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Detect whether this is Windows."""
import os

from ...base.context import context
from .. import CondaVirtualPackage, hookimpl


@hookimpl
def conda_virtual_packages():
    if not context.subdir.startswith("win-"):
        return

    dist_version = os.environ.get("CONDA_OVERRIDE_WIN")
    if not dist_version:
        dist_name, dist_version = context.os_distribution_name_version
        if dist_name != "Windows":
            # avoid reporting platform.version() of other OS
            # this happens with CONDA_SUBDIR=win-* in a non Windows machine
            dist_version = None
    yield CondaVirtualPackage("win", dist_version, None)
