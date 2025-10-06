# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Detect whether this is Windows."""

from ...base.context import context
from .. import hookimpl
from ..types import CondaVirtualPackage


def win_version():
    dist_name, dist_version = context.os_distribution_name_version
    if dist_name != "Windows":
        # dist_version is only valid if we are on Windows
        # this happens with `CONDA_SUBDIR=win-*`/`--platform=win-*` on a non-Windows machine
        dist_version = None
    return dist_version


@hookimpl
def conda_virtual_packages():
    if not context.subdir.startswith("win-"):
        return
    yield CondaVirtualPackage(
        name="win",
        version=win_version,
        build=None,
        override_entity="version",
    )
