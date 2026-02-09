# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Detect whether this is macOS."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ...base.context import context
from .. import hookimpl
from ..types import CondaVirtualPackage

if TYPE_CHECKING:
    from collections.abc import Iterable


def osx_version() -> str | None:
    dist_name, dist_version = context.os_distribution_name_version
    if dist_name != "OSX":
        # dist_version is only valid if we are on macOS
        # this happens with `CONDA_SUBDIR=osx-*`/`--platform=osx-*` on a non-macOS machine
        dist_version = None
    return dist_version


@hookimpl
def conda_virtual_packages() -> Iterable[CondaVirtualPackage]:
    if not context.subdir.startswith("osx-"):
        return

    # 1: __unix==0=0 (always exported if the target subdir is osx-*)
    yield CondaVirtualPackage(
        name="unix",
        version=None,
        build=None,
        # override_entity=None,  # no override allowed
    )

    # 2: __osx==VERSION=0
    yield CondaVirtualPackage(
        name="osx",
        version=osx_version,
        build=None,
        override_entity="version",
        # empty_override=NULL,  # falsy override → skip __osx
    )
