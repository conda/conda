# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from conda import plugins
from conda.models.plugins import CondaVirtualPackage


@plugins.hookimpl
def conda_virtual_packages():
    from conda.core.index import get_archspec_name

    yield CondaVirtualPackage("archspec", get_archspec_name())
