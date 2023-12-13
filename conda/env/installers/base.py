# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Dynamic installer loading."""
import importlib

from ...exceptions import InvalidInstaller


def get_installer(name):
    """
        Gets the installer for the given environment.

    Args:
        name (_type_): _description_

    Raises:
        InvalidInstaller: _description_

    Returns:
        _type_: _description_
    """
    try:
        return importlib.import_module(f"conda.env.installers.{name}")
    except ImportError:
        raise InvalidInstaller(name)
