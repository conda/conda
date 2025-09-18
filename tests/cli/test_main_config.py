# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

import conda.exceptions
from conda.base.constants import SafetyChecks
from conda.base.context import context, reset_context
from conda.cli.main_config import (
    _get_key,
    _key_exists,
    _read_rc,
    _remove_item,
    _remove_key,
    _set_key,
    _write_rc,
    set_keys,
)
from conda.common.configuration import DEFAULT_CONDARC_FILENAME
from conda.exceptions import CondaKeyError, EnvironmentLocationNotFound

if TYPE_CHECKING:
    from collections.abc import Iterable
    from typing import Any

    from pytest import MonkeyPatch
    from pytest_mock import MockerFixture

    from conda.common.configuration import Configuration
    from conda.testing.fixtures import (
        CondaCLIFixture,
        PathFactoryFixture,
    )


@pytest.mark.parametrize(
    "args",
    [
        pytest.param(("--get",), id="get"),
        pytest.param(("--get", "channels"), id="key"),
        pytest.param(("--get", "use_pip"), id="unknown"),
    ],
)
def test_config_get_user(conda_cli: CondaCLIFixture, args: Iterable[str]):
    stdout, _, _ = conda_cli("config", "--json", *args)
    parsed = json.loads(stdout.strip())
    assert "get" in parsed
    assert "rc_path" in parsed
    assert parsed["success"]
    assert "warnings" in parsed


@pytest.mark.skipif(not context.root_writable, reason="not root writable")
@pytest.mark.parametrize(
    "args",
    [
        pytest.param(("--get",), id="get"),
        pytest.param(("--get", "channels"), id="key"),
        pytest.param(("--get", "use_pip"), id="unknown"),
    ],
)
def test_config_get_system(conda_cli: CondaCLIFixture, args: Iterable[str]):
    stdout, _, _ = conda_cli("config", "--json", *args, "--system")
    parsed = json.loads(stdout.strip())
    assert "get" in parsed
    assert "rc_path" in parsed
    assert parsed["success"]
    assert "warnings" in parsed


@pytest.mark.parametrize(
    "args",
    [
        pytest.param(("--get",), id="get"),
        pytest.param(("--get", "channels"), id="key"),
        pytest.param(("--get", "use_pip"), id="unknown"),
    ],
)
def test_config_get_missing(
    conda_cli: CondaCLIFixture,
    args: Iterable[str],
    path_factory: PathFactoryFixture,
):
    path = path_factory()
    stdout, _, _ = conda_cli("config", "--json", *args, "--file", path)
    parsed = json.loads(stdout.strip())
    assert "get" in parsed
    assert Path(parsed["rc_path"]) == path
    assert parsed["success"]
    assert "warnings" in parsed


def test_config_show_sources_json(conda_cli: CondaCLIFixture):
    stdout, stderr, err = conda_cli("config", "--show-sources", "--json")
    parsed = json.loads(stdout.strip())
    assert "error" not in parsed  # not an error rendered as a json
    assert not stderr
    assert not err


def test_config_get_key(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("CONDA_JSON", "true")
    reset_context()
    assert context.json

    json: dict[str, Any]
    warnings: list[str]

    # undefined
    _get_key("changeps1", {}, json=(json := {}), warnings=(warnings := []))
    assert not json
    assert not warnings

    # defined
    config = {"changeps1": True, "auto_stack": 5, "channels": ["foo", "bar"]}
    _get_key("changeps1", config, json=(json := {}), warnings=(warnings := []))
    assert json == {"changeps1": True}
    assert not warnings

    _get_key("auto_stack", config, json=(json := {}), warnings=(warnings := []))
    assert json == {"auto_stack": 5}
    assert not warnings

    _get_key("channels", config, json=(json := {}), warnings=(warnings := []))
    assert json == {"channels": ["foo", "bar"]}
    assert not warnings

    # unknown
    _get_key("unknown", {}, json=(json := {}), warnings=(warnings := []))
    assert not json
    assert warnings == ["Unknown key: 'unknown'"]


def test_config_set_key(capsys) -> None:
    config: dict[str, Any] = {}

    with pytest.raises(CondaKeyError, match=r"'unknown': unknown parameter"):
        _set_key("unknown", None, config)

    # undefined
    _set_key("changeps1", True, config)
    assert config["changeps1"]

    _set_key("proxy_servers.http", "http://example.com", config)
    assert config["proxy_servers"]["http"] == "http://example.com"

    # defined
    _set_key("changeps1", False, config)
    assert not config["changeps1"]

    _set_key("proxy_servers.http", "http://other.com", config)
    assert config["proxy_servers"]["http"] == "http://other.com"

    # invalid
    with pytest.raises(CondaKeyError, match=r"'channels': invalid parameter"):
        _set_key("channels", None, config)


def test_config_remove_item() -> None:
    config: dict[str, Any] = {}

    # unknown
    with pytest.raises(CondaKeyError, match=r"'unknown': unknown parameter"):
        _remove_item("unknown", None, config)

    # undefined
    with pytest.raises(
        CondaKeyError,
        match=r"'create_default_packages': undefined in config",
    ):
        _remove_item("create_default_packages", "python", config)

    # defined
    _remove_item("channels", "defaults", config)
    assert config["channels"] == []

    config = {"channels": ["foo", "bar"]}

    _remove_item("channels", "foo", config)
    assert config["channels"] == ["bar"]

    _remove_item("channels", "bar", config)
    assert config["channels"] == []

    # missing
    with pytest.raises(
        CondaKeyError,
        match=r"'channels': value 'bar' not present in config",
    ):
        _remove_item("channels", "bar", config)

    # invalid
    with pytest.raises(CondaKeyError, match=r"'changeps1': invalid parameter"):
        _remove_item("changeps1", None, config)


def test_config_remove_key() -> None:
    config: dict[str, Any] = {}

    # unknown/undefined
    with pytest.raises(CondaKeyError, match=r"'unknown': undefined in config"):
        _remove_key("unknown", config)

    with pytest.raises(CondaKeyError, match=r"'changeps1': undefined in config"):
        _remove_key("changeps1", config)

    # defined
    config = {
        "auto_stack": 5,
        "channels": ["foo", "bar"],
        "conda_build": {"foo": {"bar": 1}},
    }

    _remove_key("auto_stack", config)
    assert "auto_stack" not in config

    _remove_key("channels", config)
    assert "channels" not in config

    _remove_key("conda_build.foo.bar", config)
    assert "bar" not in config["conda_build"]["foo"]

    _remove_key("conda_build", config)
    assert "conda_build" not in config


def test_config_read_rc(tmp_path: Path) -> None:
    condarc = tmp_path / DEFAULT_CONDARC_FILENAME
    condarc.write_text("changeps1: false\nauto_stack: 5\n")

    assert _read_rc(path=condarc) == {"changeps1": False, "auto_stack": 5}


def test_config_write_rc(tmp_path: Path) -> None:
    condarc = tmp_path / DEFAULT_CONDARC_FILENAME

    _write_rc(
        condarc,
        {
            "changeps1": False,
            "auto_stack": 5,
            "safety_checks": SafetyChecks.disabled,
        },
    )
    assert condarc.read_text() == (
        "changeps1: false\nauto_stack: 5\nsafety_checks: disabled\n"
    )


def test_config_set_keys(tmp_path: Path) -> None:
    condarc = tmp_path / DEFAULT_CONDARC_FILENAME

    set_keys(("changeps1", True), path=condarc)
    assert condarc.read_text() == "changeps1: true\n"

    set_keys(("changeps1", False), path=condarc)
    assert condarc.read_text() == "changeps1: false\n"

    set_keys(("auto_stack", 5), path=condarc)
    assert condarc.read_text() == "changeps1: false\nauto_stack: 5\n"


def test_config_set_keys_aliases(tmp_path: Path, conda_cli) -> None:
    condarc = tmp_path / DEFAULT_CONDARC_FILENAME

    set_keys(("auto_activate_base", True), path=condarc)
    assert condarc.read_text() == "auto_activate: true\n"

    set_keys(("auto_activate", True), path=condarc)
    assert condarc.read_text() == "auto_activate: true\n"

    out, err, rc = conda_cli(
        "config", "--show", "auto_activate_base", "--file", condarc
    )
    assert not rc
    assert "auto_activate: True\n" == out

    out, err, rc = conda_cli("config", "--get", "auto_activate_base", "--file", condarc)
    assert not rc
    assert "--set auto_activate True\n" == out

    out, err, rc = conda_cli(
        "config", "--describe", "auto_activate_base", "--file", condarc
    )
    assert not rc
    assert "auto_activate: true" in out

    out, err, rc = conda_cli(
        "config", "--remove-key", "auto_activate_base", "--file", condarc
    )
    assert not rc


def test_config_set_and_get_key_for_env(
    conda_cli: CondaCLIFixture,
    minimal_env: Path,
) -> None:
    """
    Ensures that setting configuration for a specific environment works as expected.
    """
    test_channel_name = "my-super-special-channel"
    # add config to prefix
    conda_cli(
        "config", "--append", "channels", test_channel_name, "--prefix", minimal_env
    )

    # check config is added to the prefix config
    stdout, _, _ = conda_cli("config", "--show", "--prefix", minimal_env, "--json")
    parsed = json.loads(stdout.strip())
    assert test_channel_name in parsed["channels"]

    # check config is not added to the config of the base environment
    stdout, _, _ = conda_cli("config", "--show", "--json")
    parsed = json.loads(stdout.strip())
    assert test_channel_name not in parsed["channels"]


def test_config_env_does_not_exist(
    conda_cli: CondaCLIFixture,
) -> None:
    with pytest.raises(EnvironmentLocationNotFound):
        conda_cli(
            "config", "--get", "channels", "--prefix", "ireallydontexist", "--json"
        )


@pytest.mark.parametrize("is_json", [True, False])
def test_key_exists(monkeypatch, plugin_config, is_json):
    """
    Ensure that key_exists works as expected, testing both when key is present and
    when it is not. We also use "is_json" as a parameter to get complete branch coverage.
    """
    MockContext, app_name = plugin_config

    monkeypatch.setenv(f"{app_name}_PLUGINS_BAR", "test_value")
    monkeypatch.setenv(f"{app_name}_FOO", "another_value")
    monkeypatch.setenv(f"{app_name}_JSON", "1" if is_json else "0")

    mock_context = MockContext(search_path=())

    assert mock_context.json == is_json

    assert _key_exists("json", [], mock_context)
    assert _key_exists("foo", [], mock_context)
    assert _key_exists("plugins.bar", [], mock_context)

    assert not _key_exists("baz", [], mock_context)
    assert not _key_exists("plugins.baz", [], mock_context)


def test_config_show(
    conda_cli: CondaCLIFixture,
    monkeypatch: MonkeyPatch,
    mocker: MockerFixture,
    plugin_config: tuple[type[Configuration], str],
):
    """
    Ensure that the config show command works as expected, testing when plugin and non-plugin
    parameters are present.
    """
    mock_context, app_name = plugin_config
    mock_context = mock_context(search_path=())
    mocker.patch("conda.base.context.context", mock_context)

    monkeypatch.setenv(f"{app_name}_PLUGINS_BAR", "test_value")
    monkeypatch.setenv(f"{app_name}_FOO", "test")

    out, err, rc = conda_cli("config", "--show", "foo")

    assert out == "foo: test\n"

    out, err, rc = conda_cli("config", "--show", "plugins.bar")

    assert out == ("plugins:\n  bar: test_value\n")


def test_config_show_errors(conda_cli: CondaCLIFixture):
    """
    Ensure that the correct message is displayed when we attempt to show configuration
    parameters that don't actually exist.
    """
    with pytest.raises(
        conda.exceptions.ArgumentError,
        match="Invalid configuration parameters: \n  - foo",
    ):
        conda_cli("config", "--show", "foo")

    with pytest.raises(
        conda.exceptions.ArgumentError,
        match="Invalid configuration parameters: \n  - plugins.foo",
    ):
        conda_cli("config", "--show", "plugins.foo")


def test_config_describe(
    conda_cli: CondaCLIFixture,
    monkeypatch: MonkeyPatch,
    mocker: MockerFixture,
    plugin_config: tuple[type[Configuration], str],
):
    """
    Ensure that the config describe command works as expected, testing when plugin and non-plugin
    parameters are present.
    """
    mock_context, app_name = plugin_config
    mock_context = mock_context(search_path=())
    mocker.patch("conda.base.context.context", mock_context)

    monkeypatch.setenv(f"{app_name}_PLUGINS_BAR", "test_value")
    monkeypatch.setenv(f"{app_name}_FOO", "test")

    out, err, rc = conda_cli("config", "--describe", "foo")

    expected = (
        "# # foo (str)",
        "# #   Test foo",
        "# # ",
        "# foo: ''",
        "",
        "",
    )
    assert out == "\n".join(expected)

    out, err, rc = conda_cli("config", "--describe", "plugins.bar")

    expected = (
        "# # plugins.bar (str)",
        "# #   Test plugins.bar",
        "# # ",
        "# plugins.bar: ''",
        "",
        "",
    )
    assert out == "\n".join(expected)

    out, err, rc = conda_cli("config", "--describe", "foo", "plugins.bar")

    expected = (
        "# # foo (str)",
        "# #   Test foo",
        "# # ",
        "# foo: ''",
        "",
        "# # plugins.bar (str)",
        "# #   Test plugins.bar",
        "# # ",
        "# plugins.bar: ''",
        "",
        "",
    )
    assert out == "\n".join(expected)


def test_config_describe_json(
    conda_cli: CondaCLIFixture,
    monkeypatch: MonkeyPatch,
    mocker: MockerFixture,
    plugin_config: tuple[type[Configuration], str],
):
    """
    Ensure that the config describe command works as expected, testing when plugin and non-plugin
    parameters are present when using the --json flag.
    """
    mock_context, app_name = plugin_config
    mock_context = mock_context(search_path=())
    mocker.patch("conda.base.context.context", mock_context)

    monkeypatch.setenv(f"{app_name}_PLUGINS_BAR", "test_value")
    monkeypatch.setenv(f"{app_name}_FOO", "test")

    out, err, rc = conda_cli("config", "--describe", "foo", "--json")

    json_out = json.loads(out)
    assert json_out == [
        {
            "aliases": [],
            "default_value": "",
            "description": "Test foo",
            "element_types": ["str"],
            "name": "foo",
            "parameter_type": "primitive",
        }
    ]

    out, err, rc = conda_cli("config", "--describe", "plugins.bar", "--json")

    json_out = json.loads(out)
    assert json_out == [
        {
            "aliases": [],
            "default_value": "",
            "description": "Test plugins.bar",
            "element_types": ["str"],
            "name": "plugins.bar",
            "parameter_type": "primitive",
        }
    ]

    out, err, rc = conda_cli("config", "--describe", "foo", "plugins.bar", "--json")

    json_out = json.loads(out)
    # Sort the output to ensure consistent comparisons
    json_out_sorted = sorted(json_out, key=lambda x: x["name"])

    assert json_out_sorted == [
        {
            "aliases": [],
            "default_value": "",
            "description": "Test foo",
            "element_types": ["str"],
            "name": "foo",
            "parameter_type": "primitive",
        },
        {
            "aliases": [],
            "default_value": "",
            "description": "Test plugins.bar",
            "element_types": ["str"],
            "name": "plugins.bar",
            "parameter_type": "primitive",
        },
    ]
