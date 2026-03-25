# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Detect whether this is Linux."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from ...base.context import context
from ...common._os.linux import linux_get_libc_version
from .. import hookimpl
from ..types import CondaVirtualPackage

if TYPE_CHECKING:
    from collections.abc import Iterable


LINUX_VERSION_PATTERN = re.compile(r"\d+\.\d+(\.\d+)?(\.\d+)?")


def linux_version() -> str | None:
    dist_name, dist_version = context.platform_system_release
    if dist_name != "Linux":
        # dist_version is only valid if we are on Linux
        # this happens with `CONDA_SUBDIR=linux-*`/`--platform=linux-*` on a non-Linux machine
        dist_version = None
    return dist_version


def linux_version_validate(version: str) -> str | None:
    # By convention, the kernel release string should be three or four
    # numeric components, separated by dots, followed by vendor-specific
    # bits.  For the purposes of versioning the `__linux` virtual package,
    # discard everything after the last digit of the third or fourth
    # numeric component; note that this breaks version ordering for
    # development (`-rcN`) kernels, but that can be a TODO for later.
    match = LINUX_VERSION_PATTERN.match(version)
    return match.group() if match else None


@hookimpl
def conda_virtual_packages() -> Iterable[CondaVirtualPackage]:
    if not context.subdir.startswith("linux-"):
        return

    # 1: __unix==0=0 (always exported if target subdir is linux-*)
    yield CondaVirtualPackage(
        name="unix",
        version=None,
        build=None,
        # override_entity=None,  # no override allowed
    )

    # 2: __linux==VERSION=0 (always exported if target subdir is linux-*)
    yield CondaVirtualPackage(
        name="linux",
        version=linux_version,
        build=None,
        override_entity="version",
        empty_override=None,  # falsy override → __linux==0=0
        version_validation=linux_version_validate,
    )

    # 3: __glibc==VERSION=0 (or another applicable libc)
    libc_family, libc_version = linux_get_libc_version()
    if not (libc_family and libc_version):
        # Default to glibc when using CONDA_SUBDIR var
        libc_family = "glibc"
    yield CondaVirtualPackage(
        name=libc_family,
        version=libc_version,
        build=None,
        override_entity="version",
        # empty_override=NULL,  # falsy override → skip __glibc
    )
