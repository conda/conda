# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

import platform

from conda import plugins
from conda.models.plugins import CondaVirtualPackage


@plugins.hookimpl
def conda_virtual_packages():
    if platform.system() != "Windows":
        return

    yield CondaVirtualPackage("win", None)
