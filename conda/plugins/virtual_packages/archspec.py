# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Detect archspec name."""

import os

from .. import hookimpl
from ..types import CondaVirtualPackage


@hookimpl
def conda_virtual_packages():
    archspec_name = os.getenv("CONDA_OVERRIDE_ARCHSPEC")
    if archspec_name is None:  # no override found
        from ...core.index import get_archspec_name

        archspec_name = get_archspec_name()
        if archspec_name:
            yield CondaVirtualPackage("archspec", "1", archspec_name)
    elif archspec_name:  # truthy override found
        yield CondaVirtualPackage("archspec", "1", archspec_name)
    # if a falsey override was found, the __archspec virtual package is not exported
