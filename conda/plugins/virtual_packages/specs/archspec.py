# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from conda.plugins import hooks


@hooks.register
def conda_virtual_packages():
    from conda.core.index import get_archspec_name

    yield hooks.CondaVirtualPackage("archspec", get_archspec_name())
