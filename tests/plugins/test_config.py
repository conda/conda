# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Tests for plugin configuration
"""

from pathlib import Path

from conda.auxlib.ish import dals
from conda.common.configuration import (
    Configuration,
)
from conda.plugins.config import PluginConfig


def test_plugin_config_data_file_source(tmp_path):
    """
    Test file source of plugin configuration values
    """
    condarc = tmp_path / "condarc"

    condarc.write_text(
        dals(
            """
            plugins:
              option_one: value_one
              option_two: value_two
            """
        )
    )

    config_data = {
        path: data for path, data in Configuration._load_search_path((condarc,))
    }

    plugin_config_data = PluginConfig(config_data).raw_data

    assert plugin_config_data.get(condarc) is not None

    option_one = plugin_config_data.get(condarc).get("option_one")
    assert option_one is not None
    assert option_one.value(None) == "value_one"

    option_two = plugin_config_data.get(condarc).get("option_two")
    assert option_two is not None
    assert option_two.value(None) == "value_two"


def test_plugin_config_data_env_var_source():
    """
    Test environment variable source of plugin configuration values
    """
    raw_data = {
        "envvars": {
            "plugins_option_one": {"_raw_value": "value_one"},
            "plugins_option_two": {"_raw_value": "value_two"},
        }
    }

    plugin_config_data = PluginConfig(raw_data).raw_data

    assert plugin_config_data.get("envvars") is not None

    option_one = plugin_config_data.get("envvars").get("option_one")
    assert option_one is not None
    assert option_one.get("_raw_value") == "value_one"

    option_two = plugin_config_data.get("envvars").get("option_two")
    assert option_two is not None
    assert option_two.get("_raw_value") == "value_two"


def test_plugin_config_data_skip_bad_values():
    """
    Make sure that values that are not frozendict for file sources are skipped
    """
    path = Path("/tmp/")

    class Value:
        def value(self, _):
            return "some_value"

    raw_data = {path: {"plugins": Value()}}

    assert PluginConfig(raw_data).raw_data == {}


def test_plugins_config_from_environment(monkeypatch, plugin_config):
    """
    Test that plugins configuration is loaded from the environment.

    This test tries to better simulate the behavior of the plugin manager by creating
    several mock classes (Context and PluginConfig)
    """
    MockContext, app_name = plugin_config

    monkeypatch.setenv(f"{app_name}_PLUGINS_BAR", "test_value")
    monkeypatch.setenv(f"{app_name}_FOO", "another_value")

    context = MockContext(search_path=())

    assert context.plugins.bar == "test_value"
    assert context.foo == "another_value"


def test_plugin_config_from_file(tmp_path, plugin_config):
    """
    Test that plugins configuration is loaded from the file.

    This test tries to better simulate the behavior of the plugin manager by creating
    several mock classes (Context and PluginConfig)
    """
    MockContext, app_name = plugin_config

    condarc = tmp_path / "condarc"

    condarc.write_text(
        dals(
            """
            foo: another_value
            plugins:
              bar: test_value
            """
        )
    )

    context = MockContext(search_path=(condarc,))

    assert context.plugins.bar == "test_value"
    assert context.foo == "another_value"


def test_plugin_describe_parameters(plugin_config: PluginConfig):
    """
    Ensure that the ``describe_parameters`` method returns the correct values, specifically
    that it prepends "plugins." to the parameter name.
    """
    MockContext, app_name = plugin_config

    mock_context = MockContext(search_path=())

    # Check that the parameter names are correct
    assert mock_context.plugins.describe_parameter("bar") == {
        "aliases": (),
        "default_value": "",
        "description": "Test plugins.bar",
        "element_types": ("str",),
        "name": "plugins.bar",
        "parameter_type": "primitive",
    }
