# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Register the conda env spec for pixi.lock files."""

from .. import CondaEnvironmentSpecifier, hookimpl


@hookimpl
def conda_environment_specifiers():
    from ...env.specs.pixi_lock_file import PixiLockFile

    yield CondaEnvironmentSpecifier(
        name="pixi.lock",
        environment_spec=PixiLockFile,
    )
