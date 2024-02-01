# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import logging

import pytest

from conda import plugins
from conda.base.context import context
from conda.common.configuration import (
    ParameterLoader,
    PrimitiveParameter,
)
from conda.exceptions import PluginError
from conda.plugins.manager import CondaPluginManager

log = logging.getLogger(__name__)

#: Name for a string type parameter
STRING_PARAMETER_NAME = "string_parameter"

#: Name for a parameter that already exists
EXISTING_PARAMETER_NAME = "channels"

string_loader = ParameterLoader(
    PrimitiveParameter(STRING_PARAMETER_NAME, element_type=str),
    aliases=(STRING_PARAMETER_NAME,),
)

existing_param_loader = ParameterLoader(
    PrimitiveParameter(EXISTING_PARAMETER_NAME, element_type=str),
    aliases=(EXISTING_PARAMETER_NAME,),
)

string_config_parameter = plugins.CondaConfigurationParameter(
    name=STRING_PARAMETER_NAME,
    description="Test string type configuration parameter",
    loader=string_loader,
)

existing_config_parameter = plugins.CondaConfigurationParameter(
    name=EXISTING_PARAMETER_NAME,
    description="Test configuration parameter for an existing one",
    loader=existing_param_loader,
)


class ConfigurationParameterPlugin:
    @plugins.hookimpl
    def conda_configuration_parameters(self):
        yield string_config_parameter


class ExistingParameterPlugin:
    @plugins.hookimpl
    def conda_configuration_parameters(self):
        yield existing_config_parameter


@pytest.fixture()
def config_param_plugin_manager(
    plugin_manager: CondaPluginManager,
) -> CondaPluginManager:
    """
    Loads our ``ConfigurationParameterPlugin`` class using the ``plugin_manager`` fixture
    """
    plugin = ConfigurationParameterPlugin()
    plugin_manager.register(plugin)

    return plugin_manager


@pytest.fixture()
def existing_param_plugin_manager(
    plugin_manager: CondaPluginManager,
) -> CondaPluginManager:
    """
    Loads our ``ExistingParameterPlugin`` class using the ``plugin_manager`` fixture
    """
    plugin = ExistingParameterPlugin()
    plugin_manager.register(plugin)

    return plugin_manager


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

    assert hasattr(context, STRING_PARAMETER_NAME)


def test_load_existing_configuration_parameter(existing_param_plugin_manager):
    """
    Ensure that when we attempt to load an existing parameter, a error is raised
    """

    with pytest.raises(PluginError):
        existing_param_plugin_manager.load_configuration_parameters()
