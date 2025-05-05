# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Register the native conda installer for conda env files."""

from .. import CondaInstaller, hookimpl


@hookimpl
def conda_installers():
    from ...env.installers.native import NativeInstaller

    yield CondaInstaller(
        name="conda",
        types=("conda",),
        installer=NativeInstaller,
    )
