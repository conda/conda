# SPDX-FileCopyrightText: © 2012 Continuum Analytics, Inc. <http://continuum.io>
# SPDX-FileCopyrightText: © 2017 Anaconda, Inc. <https://www.anaconda.com>
# SPDX-License-Identifier: BSD-3-Clause
import platform

from .. import hookimpl, CondaVirtualPackage


@hookimpl
def conda_virtual_packages():
    if platform.system() != "Windows":
        return

    yield CondaVirtualPackage("win", None, None)
