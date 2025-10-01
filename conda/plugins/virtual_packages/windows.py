# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Detect whether this is Windows."""

from ...base.context import context
from .. import hookimpl
from ..types import CondaVirtualPackage


def win_version():
    dist_name, dist_version = context.os_distribution_name_version
    if dist_name != "Windows":
        # avoid reporting platform.version() of other OS
        # this happens with CONDA_SUBDIR=win-* in a non Windows machine
        dist_version = "0"
    return dist_version


@hookimpl
def conda_virtual_packages():
    if not context.subdir.startswith("win-"):
        return
    yield CondaVirtualPackage("win", win_version, None, "version")
