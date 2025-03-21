# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Register the native conda installer for conda env files."""

from .. import CondaEnvInstaller, hookimpl


@hookimpl
def conda_env_installers():
    from ...env.installers.native import dry_run, install

    yield CondaEnvInstaller(
        name="conda",
        types=("conda",),
        install=install,
        dry_run=dry_run,
    )
