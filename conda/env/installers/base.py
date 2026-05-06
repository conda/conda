# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Dynamic installer loading."""

import importlib
import os

from ...exceptions import InvalidInstaller


def get_workdir(file_path: str | None) -> str | None:
    """
    Return the directory of an environment file path, for resolving relative
    paths in installer specs (e.g., ``-e ./local_pkg``).

    Returns None for URLs or when no usable path is provided.
    """
    if not file_path:
        return None
    from ...gateways.connection.session import CONDA_SESSION_SCHEMES

    url_scheme = file_path.split("://", 1)[0]
    if url_scheme in CONDA_SESSION_SCHEMES:
        return None
    try:
        workdir = os.path.dirname(os.path.abspath(file_path))
        return workdir if os.access(workdir, os.W_OK) else None
    except (AttributeError, TypeError):
        return None


def get_installer(name):
    """
    Gets the installer for the given environment.

    Checks registered plugins first, then falls back to built-in modules.
    The ``pip`` installer is only available via the plugin hook;
    the built-in ``conda.env.installers.pip`` module is deprecated.

    Raises: InvalidInstaller if unable to load installer
    """
    from ...base.context import context

    plugin = context.plugin_manager.get_external_installer(name)
    if plugin is not None:
        return plugin

    # pip requires the conda_external_installers plugin (provided by conda-pypi)
    if name == "pip":
        raise InvalidInstaller(name)

    try:
        return importlib.import_module(f"conda.env.installers.{name}")
    except ImportError:
        raise InvalidInstaller(name)
