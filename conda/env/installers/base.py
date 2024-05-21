# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Dynamic installer loading."""

from ...deprecations import deprecated


@deprecated(
    "24.7",
    "25.1",
    addendum="Use `conda.base.context.context.plugin_manager.get_env_installer` instead.",
)
def get_installer(name):
    """
    Gets the installer for the given environment.

    Raises: InvalidInstaller if unable to load installer
    """
    from conda.base.context import context

    return context.plugin_manager.get_env_installer(name)
