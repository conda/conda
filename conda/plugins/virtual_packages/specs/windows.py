# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

import platform

from conda.plugins import hooks


@hooks.register
def conda_virtual_packages():
    if platform.system() != "Windows":
        return

    yield hooks.CondaVirtualPackage("win", None)
