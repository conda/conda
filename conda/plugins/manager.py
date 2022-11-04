# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import functools

import pluggy

from . import virtual_packages
from .hookspec import CondaSpecs, spec_name


class PluginManager(pluggy.PluginManager):
    def load_default(self):
        for plugin in virtual_packages.plugins:
            self.register(plugin)


@functools.lru_cache(maxsize=None)  # FUTURE: Python 3.9+, replace w/ functools.cache
def get_plugin_manager() -> pluggy.PluginManager:
    pm = PluginManager(spec_name)
    pm.add_hookspecs(CondaSpecs)
    pm.load_default()
    pm.load_setuptools_entrypoints(spec_name)
    return pm
