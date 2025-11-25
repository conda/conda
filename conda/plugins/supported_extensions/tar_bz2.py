# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

"""plugin for .tar.bz2"""

from conda.cli.install import install

from ... import hookimpl
from ..types import CondaSupportedExtensions


@hookimpl
def conda_supported_extensions():
    yield CondaSupportedExtensions(name="Tarball Packages Support", action=install)


# TODO
# import the appropriate install function that would be passed as the "action" of the plugin
