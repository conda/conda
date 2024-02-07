# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import logging

import pytest
from pytest import MonkeyPatch

from conda import plugins
from conda.base.context import context, reset_context
from conda.common.configuration import (
    ParameterLoader,
    PluginConfig,
    PrimitiveParameter,
    YamlRawParameter,
    yaml_round_trip_load,
)
from conda.plugins.manager import CondaPluginManager

log = logging.getLogger(__name__)

#: Name for a string type parameter
STRING_PARAMETER_NAME = "string_parameter"

#: Value for the string type parameter (used in test condarc below)
STRING_PARAMETER_VALUE = "test_value"

#: Value for the string type parameter (used in test condarc below)
STRING_PARAMETER_ENV_VAR_VALUE = "env_var_value"

#: condarc file with our test configuration parameter present
CONDARC_TEST_ONE = f"""
plugins:
  {STRING_PARAMETER_NAME}: {STRING_PARAMETER_VALUE}
"""

string_loader = ParameterLoader(
    PrimitiveParameter("", element_type=str),
    aliases=(STRING_PARAMETER_NAME,),
)

string_config_parameter = plugins.CondaConfigurationParameter(
    name=STRING_PARAMETER_NAME,
    description="Test string type configuration parameter",
    loader=string_loader,
)


class ConfigurationParameterPlugin:
    @plugins.hookimpl
    def conda_configuration_parameters(self):
        yield string_config_parameter


@pytest.fixture()
def config_param_plugin_manager(
    plugin_manager: CondaPluginManager,
) -> CondaPluginManager:
    """
    Loads our ``ConfigurationParameterPlugin`` class using the ``plugin_manager`` fixture
    """
    plugin = ConfigurationParameterPlugin()
    plugin_manager.register(plugin)

    yield plugin_manager


@pytest.fixture()
def condarc_plugin_manager(config_param_plugin_manager):
    """
    Update the context object to load our test condarc file containing a configuration parameter
    defined by a plugin.
    """
    reset_context()
    context._set_raw_data(
        {
            "testdata": YamlRawParameter.make_raw_parameters(
                "testdata", yaml_round_trip_load(CONDARC_TEST_ONE)
            )
        }
    )

    context.plugins = PluginConfig(context.raw_data)
    return config_param_plugin_manager


def test_get_configuration_parameters(config_param_plugin_manager):
    """
    Ensure the configuration parameters method returns what we expect
    """
    config_params = config_param_plugin_manager.get_configuration_parameters()
    assert len(config_params) == 1
    assert config_params.get(STRING_PARAMETER_NAME) is string_loader


def test_load_configuration_parameters(config_param_plugin_manager):
    """
    Ensure that the configuration parameter is available via the context object
    """
    config_param_plugin_manager.load_configuration_parameters()
    assert hasattr(context.plugins, STRING_PARAMETER_NAME)


def test_load_plugin_config_with_condarc(condarc_plugin_manager):
    """
    Ensure that when we define a custom plugin configuration parameter in a condarc
    file that the value shows up on the context object.
    """
    assert getattr(context.plugins, STRING_PARAMETER_NAME) == STRING_PARAMETER_VALUE


def test_load_plugin_config_with_env_var(
    monkeypatch: MonkeyPatch, config_param_plugin_manager
):
    """
    Ensure that when an environment variable is set for a plugin configuration parameter
    it is read correctly.
    """
    monkeypatch.setenv(
        f"CONDA_PLUGINS_{STRING_PARAMETER_NAME.upper()}", STRING_PARAMETER_ENV_VAR_VALUE
    )
    reset_context()
    context.plugins = PluginConfig(context.raw_data)

    assert (
        getattr(context.plugins, STRING_PARAMETER_NAME)
        == STRING_PARAMETER_ENV_VAR_VALUE
    )
