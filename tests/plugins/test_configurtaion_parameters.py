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
from conda.plugins.manager import CondaPluginManager

log = logging.getLogger(__name__)

STRING_PARAMETER_NAME = "string_parameter"

string_loader = ParameterLoader(
    PrimitiveParameter(STRING_PARAMETER_NAME, element_type=str),
    aliases=(STRING_PARAMETER_NAME,),
)

string_config_parameter = plugins.CondaConfigurationParameter(
    name=STRING_PARAMETER_NAME,
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
    and returns a ``plugin_manager``
    """
    plugin = ConfigurationParameterPlugin()
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
