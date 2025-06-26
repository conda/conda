# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Handles plugin configuration functionality including:
  - Managing plugin-specific settings
  - Processing configuration data from various sources
  - Dynamically adding and removing plugin settings
  - Providing a standardized interface for plugins to access their configurations
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from typing import TYPE_CHECKING

from ..common.configuration import (
    Configuration,
    EnvRawParameter,
    ParameterLoader,
)

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Any

    from ..common.configuration import Parameter, RawParameter


class PluginConfig(Configuration):
    """
    Class used to hold settings for conda plugins.

    The object created by this class should only be accessed via
    :class:`conda.base.context.Context.plugins`.

    When this class is updated via the :func:`add_plugin_setting` function it adds new setting
    properties which can be accessed later via the context object.

    We currently call that function in
    :meth:`conda.plugins.manager.CondaPluginManager.load_settings`.
    because ``CondaPluginManager`` has access to all registered plugin settings via the settings
    plugin hook.
    """

    parameter_names: tuple[str, ...] = ()
    parameter_names_and_aliases: tuple[str, ...] = ()

    @classmethod
    def add_plugin_setting(
        cls, name: str, parameter: Parameter, aliases: tuple[str, ...] = ()
    ):
        """
        Adds a setting to the :class:`PluginConfig` class
        """
        cls.parameter_names = (*cls.parameter_names, name)
        loader = ParameterLoader(parameter, aliases=aliases)
        name = loader._set_name(name)
        setattr(cls, name, loader)

        # Rebuild parameter_names_and_aliases to include the new parameter
        cls._set_parameter_names_and_aliases()

    @classmethod
    def remove_all_plugin_settings(cls) -> None:
        """
        Removes all attached settings from the :class:`PluginConfig` class
        """
        for name in cls.parameter_names:
            try:
                delattr(cls, name)
            except AttributeError:
                continue

        cls.parameter_names = tuple()

    def __init__(self, data):
        self._cache_ = {}
        self._data = data

    @property
    def raw_data(self) -> dict[Path, dict[str, RawParameter]]:
        """
        This is used to move everything under the key "plugins" from the provided dictionary
        to the top level of the returned dictionary. The returned dictionary is then passed
        to :class:`PluginConfig`.
        """
        new_data = defaultdict(dict)

        for source, config in self._data.items():
            if plugin_data := config.get("plugins"):
                plugin_data_value = plugin_data.value(None)

                if not isinstance(plugin_data_value, Mapping):
                    continue

                for param_name, raw_param in plugin_data_value.items():
                    new_data[source][param_name] = raw_param

            elif source == EnvRawParameter.source:
                for env_var, raw_param in config.items():
                    if env_var.startswith("plugins_"):
                        _, param_name = env_var.split("plugins_")
                        new_data[source][param_name] = raw_param

        return new_data

    @property
    def category_map(self) -> dict[str, tuple[str, ...]]:
        return {"Additional settings provided by plugins": self.parameter_names}

    def get_descriptions(self) -> dict[str, str]:
        from ..base.context import context

        return {
            name: setting.description
            for name, setting in context.plugin_manager.get_settings().items()
        }

    def describe_parameter(self, parameter_name) -> dict[str, Any]:
        """
        Returns the description of a parameter.

        We add to this method in order to change the "name" key that is returned to prepend "plugins."
        to it.
        """
        description = super().describe_parameter(parameter_name)
        description["name"] = f"plugins.{description['name']}"

        return description
