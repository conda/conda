# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import json
import logging
from contextlib import nullcontext

import pytest
from pytest import MonkeyPatch
from ruamel.yaml import YAML

from conda import plugins
from conda.base.context import context, reset_context
from conda.common.configuration import (
    MapParameter,
    PrimitiveParameter,
    SequenceParameter,
    YamlRawParameter,
)
from conda.common.serialize import yaml
from conda.exceptions import ArgumentError, CondaKeyError
from conda.plugins.manager import CondaPluginManager

log = logging.getLogger(__name__)

STRING_PARAMETER_NAME = "string_parameter"
"""Name for a string type parameter."""
STRING_PARAMETER_ALIAS = "string_parameter_alias"

SEQ_PARAMETER_NAME = "seq_parameter"
"""Name for a sequence type parameter."""

MAP_PARAMETER_NAME = "map_parameter"
"""Name for a map type parameter."""

STRING_PARAMETER_VALUE = "test_value"
"""Value for the string type parameter (used in test condarc below)."""

STRING_PARAMETER_ENV_VAR_VALUE = "env_var_value"
"""Value for the string type parameter (used in test condarc below)."""

CONDARC_TEST_ONE = f"""
plugins:
  {STRING_PARAMETER_NAME}: {STRING_PARAMETER_VALUE}
"""
"""condarc file with our test setting present."""

string_parameter = PrimitiveParameter("", element_type=str)
seq_parameter = SequenceParameter(PrimitiveParameter("", element_type=str))
map_parameter = MapParameter(PrimitiveParameter("", element_type=str))

string_config_parameter = plugins.types.CondaSetting(
    name=STRING_PARAMETER_NAME,
    description="Test string type setting",
    parameter=string_parameter,
    aliases=(STRING_PARAMETER_ALIAS,),
)

sequence_config_parameter = plugins.types.CondaSetting(
    name=SEQ_PARAMETER_NAME,
    description="Test sequence type setting",
    parameter=seq_parameter,
)

map_config_parameter = plugins.types.CondaSetting(
    name=MAP_PARAMETER_NAME,
    description="Test map type setting",
    parameter=map_parameter,
)


class SettingPlugin:
    @plugins.hookimpl
    def conda_settings(self):
        yield string_config_parameter
        yield sequence_config_parameter
        yield map_config_parameter


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
                "testdata", yaml.loads(CONDARC_TEST_ONE)
            )
        }
    )

    return setting_plugin_manager


def test_get_settings(setting_plugin_manager):
    """
    Ensure the settings method returns what we expect
    """
    config_params = setting_plugin_manager.get_settings()
    assert len(config_params) == 3

    string_setting = config_params.get(STRING_PARAMETER_NAME)

    assert string_setting.name == STRING_PARAMETER_NAME
    assert string_setting.aliases == (STRING_PARAMETER_ALIAS,)

    seq_setting = config_params.get(SEQ_PARAMETER_NAME)

    assert seq_setting.name == SEQ_PARAMETER_NAME
    assert seq_setting.aliases == ()

    map_setting = config_params.get(MAP_PARAMETER_NAME)

    assert map_setting.name == MAP_PARAMETER_NAME
    assert map_setting.aliases == ()


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


def test_conda_config_with_string_settings(condarc_plugin_manager, tmp_path, conda_cli):
    """
    Ensure that string parameter types work correctly as a plugin setting
    """
    condarc = tmp_path / "condarc"
    out, err, _ = conda_cli(
        "config",
        "--file",
        condarc,
        "--set",
        f"plugins.{STRING_PARAMETER_NAME}",
        "env_var_value",
    )

    assert not err
    assert not out

    assert "plugins:\n  string_parameter: env_var_value\n" in condarc.read_text()

    out, *_ = conda_cli(
        "config", "--file", condarc, "--get", f"plugins.{STRING_PARAMETER_NAME}"
    )

    assert out == "--set plugins.string_parameter env_var_value\n"

    out, err, _ = conda_cli(
        "config", "--file", condarc, "--remove-key", f"plugins.{STRING_PARAMETER_NAME}"
    )

    assert not out
    assert not err


def test_conda_config_with_sequence_settings(
    condarc_plugin_manager, tmp_path, conda_cli
):
    """
    Ensure that sequence parameter types work correctly as a plugin setting
    """
    condarc = tmp_path / "condarc"
    out, err, _ = conda_cli(
        "config",
        "--file",
        condarc,
        "--add",
        f"plugins.{SEQ_PARAMETER_NAME}",
        "value_one",
    )

    assert not err
    assert not out

    assert "plugins:\n  seq_parameter:\n    - value_one\n" in condarc.read_text()

    out, *_ = conda_cli(
        "config", "--file", condarc, "--get", f"plugins.{SEQ_PARAMETER_NAME}"
    )

    assert out == "--add plugins.seq_parameter 'value_one'\n"
    assert not err

    out, err, _ = conda_cli(
        "config",
        "--file",
        condarc,
        "--remove",
        f"plugins.{SEQ_PARAMETER_NAME}",
        "value_one",
    )

    assert not out
    assert not err


def test_conda_config_with_map_settings(condarc_plugin_manager, tmp_path, conda_cli):
    """
    Ensure that sequence parameter types work correctly as a plugin setting
    """
    condarc = tmp_path / "condarc"
    out, err, _ = conda_cli(
        "config",
        "--file",
        condarc,
        "--set",
        f"plugins.{MAP_PARAMETER_NAME}.key",
        "value_one",
    )

    assert not err
    assert not out

    assert "plugins:\n  map_parameter:\n    key: value_one\n" in condarc.read_text()

    out, *_ = conda_cli(
        "config", "--file", condarc, "--get", f"plugins.{MAP_PARAMETER_NAME}.key"
    )

    assert out == f"--set plugins.{MAP_PARAMETER_NAME}.key value_one\n"

    out, err, _ = conda_cli(
        "config", "--file", condarc, "--remove-key", f"plugins.{MAP_PARAMETER_NAME}"
    )

    assert not out
    assert not err


def test_conda_config_with_invalid_setting(condarc_plugin_manager, tmp_path, conda_cli):
    """
    Ensure that an error is raised when an invalid setting is passed to the config command
    """
    condarc = tmp_path / "condarc"

    with pytest.raises(
        CondaKeyError, match=r"'plugins.invalid_setting': unknown parameter"
    ):
        out, err, _ = conda_cli(
            "config",
            "--file",
            condarc,
            "--set",
            "plugins.invalid_setting",
            "value_one",
        )


def test_conda_config_describe_includes_plugin_settings(
    condarc_plugin_manager, conda_cli
):
    """
    Ensure that the describe command includes plugin settings
    """
    out, err, _ = conda_cli("config", "--describe")

    section_banner = (
        "# ######################################################\n"
        "# ##     Additional settings provided by plugins      ##\n"
        "# ######################################################"
    )

    assert not err
    assert section_banner in out

    # Headers display dotted notation for settings, as it's easier to
    # read. The YAML representation uses nested notation.

    assert f"# # plugins.{STRING_PARAMETER_NAME}" in out
    assert f"# # plugins.{SEQ_PARAMETER_NAME}" in out
    assert f"# # plugins.{MAP_PARAMETER_NAME}" in out

    assert f"# plugins:\n#   {STRING_PARAMETER_NAME}:" in out
    assert f"# plugins:\n#   {SEQ_PARAMETER_NAME}:" in out
    assert f"# plugins:\n#   {MAP_PARAMETER_NAME}:" in out


def test_conda_config_describe_not_included_without_plugins(conda_cli, mocker):
    """
    Ensure that the describe command does not include the section banner
    for plugins when no additional settings are provided by plugins
    """
    mock = mocker.patch("conda.plugins.manager.CondaPluginManager.get_hook_results")
    mock.return_value = []
    out, err, _ = conda_cli("config", "--describe")

    section_banner = (
        "# ######################################################\n"
        "# ##     Additional settings provided by plugins      ##\n"
        "# ######################################################"
    )

    assert not err
    assert section_banner not in out


def test_conda_config_describe_unknown_plugin_setting(
    condarc_plugin_manager, conda_cli
):
    """
    Ensure that the correct error message is displayed when an unknown plugin setting is used
    """
    with pytest.raises(
        ArgumentError,
        match="Invalid configuration parameters: \n  - plugins.invalid_setting",
    ):
        conda_cli("config", "--describe", "plugins.invalid_setting")


def test_conda_config_show_includes_plugin_settings(
    monkeypatch: MonkeyPatch, condarc_plugin_manager, conda_cli, tmp_path
):
    """
    Ensure that the show command includes plugin settings
    """
    condarc = tmp_path / "condarc"
    monkeypatch.setenv("CONDARC", str(condarc))
    out, err, _ = conda_cli(
        "config",
        "--file",
        condarc,
        "--set",
        f"plugins.{STRING_PARAMETER_NAME}",
        "value_one",
    )

    # TODO: a deprecation warning is emitted for `error_upload_url`.
    with pytest.deprecated_call():
        out, err, _ = conda_cli("config", "--show")
        config_data = YAML().load(out)

        assert not err
        assert config_data["plugins"][STRING_PARAMETER_NAME] == "value_one"
        assert config_data["plugins"][SEQ_PARAMETER_NAME] == []
        assert config_data["plugins"][MAP_PARAMETER_NAME] == {}

        out, err, _ = conda_cli("config", "--show", "--json")

        config_data = json.loads(out)
        assert config_data["plugins"][STRING_PARAMETER_NAME] == "value_one"
        assert config_data["plugins"][SEQ_PARAMETER_NAME] == []
        assert config_data["plugins"][MAP_PARAMETER_NAME] == {}


@pytest.mark.parametrize(
    "parameter_name, expected_output",
    [
        (STRING_PARAMETER_NAME, "plugins:\n  string_parameter: value_one\n"),
        (SEQ_PARAMETER_NAME, "plugins:\n  seq_parameter: []\n"),
        (MAP_PARAMETER_NAME, "plugins:\n  map_parameter: {}\n"),
        (
            "non_existent_parameter",
            ArgumentError(
                "Invalid configuration parameters: \n  - plugins.non_existent_parameter"
            ),
        ),
    ],
)
def test_conda_config_show_for_individual_settings(
    monkeypatch: MonkeyPatch,
    condarc_plugin_manager,
    conda_cli,
    tmp_path,
    parameter_name,
    expected_output,
):
    """
    Ensure that the show command includes plugin settings
    """
    condarc = tmp_path / "condarc"
    monkeypatch.setenv("CONDARC", str(condarc))
    out, err, _ = conda_cli(
        "config",
        "--file",
        condarc,
        "--set",
        f"plugins.{STRING_PARAMETER_NAME}",
        "value_one",
    )

    with (
        pytest.raises(ArgumentError, match=expected_output.message)
        if isinstance(expected_output, Exception)
        else nullcontext()
    ):
        out, err, _ = conda_cli("config", "--show", f"plugins.{parameter_name}")
        assert not err
        assert out == expected_output


@pytest.mark.parametrize(
    "parameter_name, expected_description",
    [
        (STRING_PARAMETER_NAME, "Test string type setting"),
        (SEQ_PARAMETER_NAME, "Test sequence type setting"),
        (MAP_PARAMETER_NAME, "Test map type setting"),
    ],
)
def test_conda_config_retrieves_correct_description_single_setting(
    condarc_plugin_manager, conda_cli, parameter_name, expected_description
):
    """
    Ensure that the describe command includes the correct description when
    retrieving individual plugin descriptions
    """
    out, err, _ = conda_cli("config", "--describe", f"plugins.{parameter_name}")

    assert not err
    assert expected_description in out
