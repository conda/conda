# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

import os
import platform

from conda import plugins


@plugins.register
def conda_virtual_packages():
    if platform.system() != "Darwin":
        return

    yield plugins.CondaVirtualPackage("unix", None)

    dist_version = os.environ.get("CONDA_OVERRIDE_OSX", platform.mac_ver()[0])
    yield plugins.CondaVirtualPackage("osx", dist_version)
