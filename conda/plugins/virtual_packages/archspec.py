# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Detect archspec name."""

from ...auxlib import NULL
from .. import hookimpl
from ..types import CondaVirtualPackage


def archspec_build_num():
    from ...core.index import get_archspec_name

    build_num = get_archspec_name()
    return build_num or NULL


@hookimpl
def conda_virtual_packages():
    yield CondaVirtualPackage(
        name="archspec",
        version="1",
        build=archspec_build_num,
        override_entity="build",
    )
    # if a falsey override was found, the __archspec virtual package is not exported
