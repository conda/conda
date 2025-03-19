# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Dynamic installer loading."""


def get_installer(name):
    """
    Gets the installer for the given environment.

    Raises: InvalidInstaller if unable to load installer
    """
    from conda.base.context import context

    return context.plugin_manager.get_env_installer(name)
