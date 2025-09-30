# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Detect whether this is macOS."""

from ...base.context import context
from .. import hookimpl
from ..types import CondaVirtualPackage


def osx_version():
    dist_name, dist_version = context.os_distribution_name_version
    if dist_name != "OSX":
        # avoid reporting platform.version() of a different OS
        # this happens with CONDA_SUBDIR=osx-* in a non macOS machine or when `--platform` is used on the CLI
        dist_version = "0"
    return dist_version


@hookimpl
def conda_virtual_packages():
    if not context.subdir.startswith("osx-"):
        return
    # 1: __osx (always exported if the target subdir is osx-*)
    yield CondaVirtualPackage("unix", None, None, "version")
    # 2: __osx
    yield CondaVirtualPackage("osx", osx_version, None, "version")
    # if a falsey override was found, the __osx virtual package is not exported
