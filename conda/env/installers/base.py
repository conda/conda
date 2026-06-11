# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Dynamic installer loading."""

import importlib

from ...exceptions import InvalidInstaller


def get_installer(name):
    """Load the environment installer module for the given name.

    Args:
        name: Installer name (e.g., ``conda`` or ``pip``).

    Raises:
        InvalidInstaller: If no installer module can be imported for ``name``.
    """
    try:
        return importlib.import_module(f"conda.env.installers.{name}")
    except ImportError:
        raise InvalidInstaller(name)
