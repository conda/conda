# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import logging

import pytest
from pytest import MonkeyPatch

from conda import plugins
from conda.base.context import context, reset_context
from conda.common.configuration import (
    PrimitiveParameter,
    YamlRawParameter,
    yaml_round_trip_load,
)
from conda.plugins.manager import CondaPluginManager

log = logging.getLogger(__name__)

#: Name for a string type parameter
STRING_PARAMETER_NAME = "string_parameter"
STRING_PARAMETER_ALIAS = "string_parameter_alias"

#: Value for the string type parameter (used in test condarc below)
STRING_PARAMETER_VALUE = "test_value"

#: Value for the string type parameter (used in test condarc below)
STRING_PARAMETER_ENV_VAR_VALUE = "env_var_value"

#: condarc file with our test setting present
CONDARC_TEST_ONE = f"""
plugins:
  {STRING_PARAMETER_NAME}: {STRING_PARAMETER_VALUE}
"""

string_parameter = PrimitiveParameter("", element_type=str)

string_config_parameter = plugins.CondaSetting(
    name=STRING_PARAMETER_NAME,
    description="Test string type setting",
    parameter=string_parameter,
    aliases=(STRING_PARAMETER_ALIAS,),
)


class SettingPlugin:
    @plugins.hookimpl
    def conda_settings(self):
        yield string_config_parameter


@pytest.fixture()
def clear_plugins_context_cache():
    """
    This fixture is used to ensure that the cache on the property ``plugins`` for the ``context``
    object is cleared before each test run.

    More info: https://docs.python.org/3/library/functools.html#functools.cached_property
    """

    try:
        del context.plugins  # clear cached property
    except AttributeError:
        pass


@pytest.fixture()
def setting_plugin_manager(
    plugin_manager: CondaPluginManager, clear_plugins_context_cache
) -> CondaPluginManager:
    """
    Loads our ``SettingPlugin`` class using the ``plugin_manager`` fixture
    """
    plugin = SettingPlugin()
    plugin_manager.register(plugin)

    yield plugin_manager


@pytest.fixture()
def condarc_plugin_manager(setting_plugin_manager):
    """
    Update the context object to load our test condarc file containing a setting
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

    return setting_plugin_manager


def test_get_settings(setting_plugin_manager):
    """
    Ensure the settings method returns what we expect
    """
    config_params = setting_plugin_manager.get_settings()
    assert len(config_params) == 1
    assert config_params.get(STRING_PARAMETER_NAME) == (
        string_parameter,
        (STRING_PARAMETER_ALIAS,),
    )


def test_load_configuration_parameters(setting_plugin_manager):
    """
    Ensure that the setting is available via the context object
    """
    setting_plugin_manager.load_settings()
    assert hasattr(context.plugins, STRING_PARAMETER_NAME)


def test_load_plugin_settings_with_condarc(condarc_plugin_manager):
    """
    Ensure that when we define a custom plugin setting in a condarc
    file that the value shows up on the context object.
    """
    assert getattr(context.plugins, STRING_PARAMETER_NAME) == STRING_PARAMETER_VALUE


def test_load_plugin_config_with_env_var(
    monkeypatch: MonkeyPatch, setting_plugin_manager
):
    """
    Ensure that when an environment variable is set for a plugin setting
    it is read correctly.
    """
    monkeypatch.setenv(
        f"CONDA_PLUGINS_{STRING_PARAMETER_NAME.upper()}", STRING_PARAMETER_ENV_VAR_VALUE
    )
    reset_context()

    assert (
        getattr(context.plugins, STRING_PARAMETER_NAME)
        == STRING_PARAMETER_ENV_VAR_VALUE
    )
