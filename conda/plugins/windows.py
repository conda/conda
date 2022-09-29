# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

import platform

from .. import plugins


@plugins.register
def conda_virtual_package_plugin():
    if platform.system() != "Windows":
        return

    yield plugins.CondaVirtualPackage("win", None)
