# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Register the pip installer for conda env files."""

from .. import CondaInstaller, hookimpl


@hookimpl
def conda_env_installers():
    from ...env.installers.pip import PipInstaller

    yield CondaInstaller(
        name="pip",
        types=("pip",),
        installer=PipInstaller,
    )
