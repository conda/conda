# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Detect whether this is macOS."""

import os
from subprocess import check_output

from ...base.context import context
from ...models.version import VersionOrder
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
        elif VersionOrder("10.15") < VersionOrder(dist_version) < VersionOrder("11"):
            # https://github.com/conda/conda/issues/13832
            # If Python was compiled against macOS <=10.15, we might get 10.16 instead of 11.0.
            # For these cases, we must set SYSTEM_VERSION_COMPAT=0 and call sw_vers directly.
            dist_version = non_compat_mac_ver() or "0"
    if dist_version:
        yield CondaVirtualPackage("osx", dist_version, None)


def non_compat_mac_ver() -> str:
    return check_output(
        ["/usr/bin/sw_vers", "-productVersion"],
        env={"SYSTEM_VERSION_COMPAT": "0"},
        text=True,
    ).strip()
