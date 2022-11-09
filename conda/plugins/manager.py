# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import functools

import pluggy

from . import virtual_packages
from .hookspec import CondaSpecs, spec_name
from ..exceptions import PluginError


class CondaPluginManager(pluggy.PluginManager):
    """
    The conda plugin manager to implement behavior additional to
    pluggy's default plugin manager.
    """
    def __init__(self, project_name: str | None = None, *args, **kwargs):
        # Setting the default project name to the spec name for ease of use
        if project_name is None:
            project_name = spec_name
        super().__init__(project_name, *args, **kwargs)

    def load_plugins(self, *plugins) -> list[str]:
        """
        Load the provided list of plugins and fail gracefully on failure.
        """
        plugin_names = []
        for plugin in plugins:
            try:
                plugin_name = self.register(plugin)
            except ValueError as err:
                raise PluginError(f"Error while registering conda plugins: {err}")
            else:
                plugin_names.append(plugin_name)
        return plugin_names


@functools.lru_cache(maxsize=None)  # FUTURE: Python 3.9+, replace w/ functools.cache
def get_plugin_manager() -> CondaPluginManager:
    pm = CondaPluginManager()
    pm.add_hookspecs(CondaSpecs)
    pm.load_plugins(*virtual_packages.plugins)
    pm.load_setuptools_entrypoints(spec_name)
    return pm
