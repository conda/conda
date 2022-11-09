# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from .. import hookimpl, CondaVirtualPackage


@hookimpl
def conda_virtual_packages():
    from ...core.index import get_archspec_name

    yield CondaVirtualPackage("archspec", get_archspec_name())
