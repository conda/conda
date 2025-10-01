# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Detect whether this is Linux."""

import re

from ...base.context import context
from ...common._os.linux import linux_get_libc_version
from .. import hookimpl
from ..types import CondaVirtualPackage


def linux_version():
    dist_name, dist_version = context.platform_system_release
    if dist_name != "Linux":  # dist_version is only valid if we are on Linux!
        dist_version = "0"
    return dist_version


def linux_version_validate(version: str) -> str:
    linux_version_pattern = re.compile(r"\d+\.\d+(\.\d+)?(\.\d+)?")
    match = linux_version_pattern.match(version)
    return match.group() if match else "0"


@hookimpl
def conda_virtual_packages():
    if not context.subdir.startswith("linux-"):
        return

    # 1: __unix (lways exported if target subdir is linux-*)
    yield CondaVirtualPackage("unix", None, None)

    # 2: __linux (always exported if target subdir is linux-*)
    # By convention, the kernel release string should be three or four
    # numeric components, separated by dots, followed by vendor-specific
    # bits.  For the purposes of versioning the `__linux` virtual package,
    # discard everything after the last digit of the third or fourth
    # numeric component; note that this breaks version ordering for
    # development (`-rcN`) kernels, but that can be a TODO for later.

    yield CondaVirtualPackage(
        "linux", linux_version, None, "version", "0", linux_version_validate
    )

    # 3: __glibc (or another applicable libc)
    libc_family, libc_version = linux_get_libc_version()
    if not (libc_family and libc_version):
        # Default to glibc when using CONDA_SUBDIR var
        libc_family = "glibc"
    yield CondaVirtualPackage(libc_family, libc_version, None, "version")
    # if a falsey override was found, the __glibc virtual package is not exported
