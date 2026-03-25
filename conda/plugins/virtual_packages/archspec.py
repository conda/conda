# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Detect archspec name."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ...auxlib import NULL
from .. import hookimpl
from ..types import CondaVirtualPackage

if TYPE_CHECKING:
    from collections.abc import Iterable


def archspec_build():
    from ...core.index import get_archspec_name

    build_num = get_archspec_name()
    return build_num or NULL


@hookimpl
def conda_virtual_packages() -> Iterable[CondaVirtualPackage]:
    # 1: __archspec==1=BUILD
    yield CondaVirtualPackage(
        name="archspec",
        version="1",
        build=archspec_build,
        override_entity="build",
        # empty_override=NULL,  # falsy override → skip __archspec
    )
