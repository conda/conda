# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Detect whether this is FeeBSD."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ...base.context import context
from .. import hookimpl
from ..types import CondaVirtualPackage

if TYPE_CHECKING:
    from collections.abc import Iterable


@hookimpl
def conda_virtual_packages() -> Iterable[CondaVirtualPackage]:
    if not context.subdir.startswith("freebsd-"):
        return

    # 1: __unix==0=0 (always exported if target subdir is freebsd-*)
    yield CondaVirtualPackage(
        name="unix",
        version=None,
        build=None,
        # override_entity=None,  # no override allowed
    )
