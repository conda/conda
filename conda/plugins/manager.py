# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import functools

import pluggy

from . import solvers, virtual_packages
from .hookspec import CondaSpecs, spec_name
from ..auxlib.ish import dals
from ..base.context import context
from ..core.solve import Solver
from ..exceptions import CondaValueError, PluginError


class CondaPluginManager(pluggy.PluginManager):
    """
    The conda plugin manager to implement behavior additional to
    pluggy's default plugin manager.
    """

    def __init__(self, project_name: str | None = None, *args, **kwargs):
        # Setting the default project name to the spec name for ease of use
        if project_name is None:
            project_name = spec_name
        # Make the cache containers local to the instances so that the
        # reference from cache to the instance gets garbage collected with the instance
        self.get_solver_backend = functools.lru_cache()(self._get_solver_backend)
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

    def get_registered_plugins(self, plugin_name: str) -> list:
        """
        Return all registered plugins for the given name.
        """
        hook_name = f"{self.project_name}_{plugin_name}"  # e.g. conda_solvers
        hook = getattr(self.hook, hook_name, None)
        if hook is None:
            raise PluginError(f"Could not load `{hook_name}` plugins.")

        plugins = sorted(
            (item for items in hook() for item in items),
            key=lambda item: item.name,
        )
        # Check for conflicts
        seen = set()
        conflicts = [plugin for plugin in plugins if plugin.name in seen or seen.add(plugin.name)]
        if conflicts:
            raise PluginError(
                dals(
                    f"""
                    Conflicting `{plugin_name}` plugins found:

                    {', '.join([str(conflict) for conflict in conflicts])}

                    Multiple conda plugins are registered via the `{hook_name}` hook.
                    Please make sure that you don't have any incompatible plugins installed.
                    """
                )
            )
        return plugins

    def _get_solver_backend(self, name: str = None) -> type[Solver]:
        """
        Get the solver backend with the given name (or fall back to the
        name provided in the context).

        See ``context.solver`` for more details.

        This is cached with a plugin manager specific LRU cache.
        """
        # Some light data validation in case name isn't given.
        if name is None:
            name = context.solver
        name = name.lower()

        # Build a mapping between a lower cased backend name and
        # solver backend class provided by the installed plugins.
        solvers_mapping = {
            solver.name.lower(): solver.backend
            for solver in self.get_registered_plugins("solvers")
        }

        # Look up the solver mapping an fail loudly if it can't
        # find the requested solver.
        backend = solvers_mapping.get(name, None)
        if backend is None:
            raise CondaValueError(
                f"You have chosen a non-default solver backend ({name}) "
                f"but it was not recognized. Choose one of: "
                f"{', '.join(solvers_mapping.keys())}"
            )

        return backend


@functools.lru_cache(maxsize=None)  # FUTURE: Python 3.9+, replace w/ functools.cache
def get_plugin_manager() -> CondaPluginManager:
    pm = CondaPluginManager()
    pm.add_hookspecs(CondaSpecs)
    pm.load_plugins(solvers, *virtual_packages.plugins)
    pm.load_setuptools_entrypoints(spec_name)
    return pm
