# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

import platform

from conda import plugins
from conda.common._os.linux import linux_get_libc_version


@plugins.hookimp
def conda_cli_register_virtual_packages():
    if platform.system != 'Darwin':
        return

    yield plugins.CondaVirtualPackage('unix', None)
    yield plugins.CondaVirtualPackage(
        'osx',
        os.environ.get('CONDA_OVERRIDE_OSX', platform.mac_ver()[0]),
    )
