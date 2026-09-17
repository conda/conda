# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import json
import os
from pathlib import Path
from stat import S_IMODE
from typing import TYPE_CHECKING

import pytest

import conda.exceptions
from conda.base.constants import SafetyChecks
from conda.base.context import context, reset_context
from conda.cli.condarc import MISSING, ConfigurationFile
from conda.cli.main_config import set_keys
from conda.common.compat import on_mac, on_win
from conda.common.configuration import DEFAULT_CONDARC_FILENAME
from conda.exceptions import (
    CondaKeyError,
    CouldntParseError,
    EnvironmentLocationNotFound,
)

if TYPE_CHECKING:
    from collections.abc import Iterable

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


def test_format_dict_mapping_items():
    from frozendict import frozendict

    from conda.cli.main_config import format_dict

    result = format_dict(
        {
            "channel_settings": [
                frozendict({"channel": "https://example.com/*", "auth": "token"}),
            ],
        }
    )
    formatted = "\n".join(result)
    assert "frozendict" not in formatted
    assert "channel_settings:" in formatted
    assert "  - channel: https://example.com/*" in formatted
    assert "    auth: token" in formatted


def test_config_get_key(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("CONDA_JSON", "true")
    reset_context()
    assert context.json

    warnings: list[str] = []
    config = ConfigurationFile(
        context=context, content={}, warning_handler=lambda msg: warnings.append(msg)
    )
    # undefined
    assert config.get_key("changeps1") == ("changeps1", MISSING)
    assert not warnings

    # unknown
    warnings = []
    assert config.get_key("unknown") == ("unknown", MISSING)
    assert warnings == ["Unknown key: 'unknown'"]

    # defined
    config = ConfigurationFile(
        context=context,
        content={"changeps1": True, "auto_stack": 5, "channels": ["foo", "bar"]},
    )
    warnings = []
    assert config.get_key("changeps1") == ("changeps1", True)
    assert not warnings

    assert config.get_key("auto_stack") == ("auto_stack", 5)
    assert not warnings

    assert config.get_key("channels") == ("channels", ["foo", "bar"])
    assert not warnings


def test_config_set_key(capsys) -> None:
    config: ConfigurationFile = ConfigurationFile(content={})

    with pytest.raises(CondaKeyError, match=r"'unknown': unknown parameter"):
        config.set_key("unknown", None)

    # undefined
    config.set_key("changeps1", True)
    assert config.content["changeps1"]

    config.set_key("proxy_servers.http", "http://example.com")
    assert config.content["proxy_servers"]["http"] == "http://example.com"

    # defined
    config.set_key("changeps1", False)
    assert not config.content["changeps1"]

    config.set_key("proxy_servers.http", "http://other.com")
    assert config.content["proxy_servers"]["http"] == "http://other.com"

    # invalid
    with pytest.raises(CondaKeyError, match=r"'channels': invalid parameter"):
        config.set_key("channels", None)


def test_config_remove_item() -> None:
    config: ConfigurationFile = ConfigurationFile(content={})

    # unknown
    with pytest.raises(CondaKeyError, match=r"'unknown': unknown parameter"):
        config.remove_item("unknown", None)

    # undefined
    with pytest.raises(
        CondaKeyError,
        match=r"'create_default_packages': undefined in config",
    ):
        config.remove_item("create_default_packages", "python")

    # defined
    config.remove_item("channels", "defaults")
    assert config.content["channels"] == []

    config = ConfigurationFile(content={"channels": ["foo", "bar"]})
    config.remove_item("channels", "foo")
    assert config.content["channels"] == ["bar"]

    config.remove_item("channels", "bar")
    assert config.content["channels"] == []

    # missing
    with pytest.raises(
        CondaKeyError,
        match=r"'channels': value 'bar' not present in config",
    ):
        config.remove_item("channels", "bar")

    # invalid
    with pytest.raises(CondaKeyError, match=r"'changeps1': invalid parameter"):
        config.remove_item("changeps1", None)


def test_config_clear_key() -> None:
    config = ConfigurationFile(
        content={
            "channels": ["defaults", "conda-forge"],
            "aggressive_update_packages": ["ca-certificates", "certifi"],
        }
    )

    config.clear_key("channels")
    assert config.content["channels"] == []

    config.clear_key("aggressive_update_packages")
    assert config.content["aggressive_update_packages"] == []

    # Clearing an undefined sequence explicitly creates an empty list.
    config.clear_key("create_default_packages")
    assert config.content["create_default_packages"] == []

    # Clearing an already-empty sequence is idempotent.
    config.clear_key("channels")
    assert config.content["channels"] == []


def test_config_clear_key_alias() -> None:
    config = ConfigurationFile(content={"disallow": ["openssl"]})

    config.clear_key("disallow")

    assert "disallow" not in config.content
    assert config.content["disallowed_packages"] == []


def test_config_clear_key_invalid() -> None:
    config = ConfigurationFile(content={"changeps1": True})

    with pytest.raises(CondaKeyError, match=r"'unknown': unknown parameter"):
        config.clear_key("unknown")

    with pytest.raises(CondaKeyError, match=r"'changeps1': invalid parameter"):
        config.clear_key("changeps1")

    with pytest.raises(CondaKeyError, match=r"'proxy_servers': invalid parameter"):
        config.clear_key("proxy_servers")


def test_config_clear_key_invalid_value_type() -> None:
    config = ConfigurationFile(content={"channels": "defaults"})

    with pytest.raises(
        CouldntParseError,
        match=r"key 'channels' should be a list, not str",
    ):
        config.clear_key("channels")


def test_config_remove_key() -> None:
    config: ConfigurationFile = ConfigurationFile(content={})

    # unknown/undefined
    with pytest.raises(CondaKeyError, match=r"'unknown': undefined in config"):
        config.remove_key("unknown")

    with pytest.raises(CondaKeyError, match=r"'changeps1': undefined in config"):
        config.remove_key("changeps1")

    # defined
    config: ConfigurationFile = ConfigurationFile(
        content={
            "auto_stack": 5,
            "channels": ["foo", "bar"],
            "conda_build": {"foo": {"bar": 1}},
        }
    )
    config.remove_key("auto_stack")
    assert "auto_stack" not in config.content

    config.remove_key("channels")
    assert "channels" not in config.content

    config.remove_key("conda_build.foo.bar")
    assert "bar" not in config.content["conda_build"]["foo"]

    config.remove_key("conda_build")
    assert "conda_build" not in config.content


def test_config_read_rc(tmp_path: Path) -> None:
    condarc = tmp_path / DEFAULT_CONDARC_FILENAME
    condarc.write_text("changeps1: false\nauto_stack: 5\n")

    assert ConfigurationFile(path=condarc).content == {
        "changeps1": False,
        "auto_stack": 5,
    }


def test_config_write_rc(tmp_path: Path) -> None:
    target_path = tmp_path / DEFAULT_CONDARC_FILENAME
    config = ConfigurationFile(
        target_path,
        content={
            "changeps1": False,
            "auto_stack": 5,
            "safety_checks": SafetyChecks.disabled,
        },
    )
    config.write()
    assert (
        target_path.read_text()
        == "changeps1: false\nauto_stack: 5\nsafety_checks: disabled\n"
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
    empty_env: Path,
) -> None:
    """
    Ensures that setting configuration for a specific environment works as expected.
    """
    test_channel_name = "my-super-special-channel"
    # add config to prefix
    conda_cli(
        "config", "--append", "channels", test_channel_name, "--prefix", empty_env
    )

    # TODO: a deprecation warning is emitted for `error_upload_url`.
    with pytest.deprecated_call():
        # check config is added to the prefix config
        stdout, _, _ = conda_cli("config", "--show", "--prefix", empty_env, "--json")
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

    config = ConfigurationFile(content={}, context=mock_context)

    assert config.key_exists("json")
    assert config.key_exists("foo")
    assert config.key_exists("plugins.bar")

    assert not config.key_exists("baz")
    assert not config.key_exists("plugins.baz")


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
        "# plugins:",
        "#   bar: ''",
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
        "# plugins:",
        "#   bar: ''",
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


def test_config_describe_plugins_yaml_format(
    conda_cli: CondaCLIFixture,
    monkeypatch: MonkeyPatch,
    mocker: MockerFixture,
    plugin_config: tuple[type[Configuration], str],
):
    """
    Regression test for the issue described in https://github.com/conda/conda/issues/15339.

    Ensure that plugin configuration examples in `conda config --describe`
    use valid nested YAML format. which is (plugins:\n  setting_name: value),
    instead of dotted notation (plugins.setting_name: value), which is
    syntactically invalid in YAML.
    """
    mock_context, app_name = plugin_config
    mock_context = mock_context(search_path=())
    mocker.patch("conda.base.context.context", mock_context)

    monkeypatch.setenv(f"{app_name}_PLUGINS_BAR", "test_value")

    out, err, rc = conda_cli("config", "--describe", "plugins.bar")

    assert "plugins:" in out
    assert "  bar: ''" in out

    assert "plugins.bar: ''" not in out


def test_config_file_from_user_condarc(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    """Test ConfigurationFile.from_user_condarc() factory method."""
    # Create a temporary user condarc
    user_condarc = tmp_path / ".condarc"
    user_condarc.write_text("channels:\n  - conda-forge\n")

    # Mock the user_rc_path
    monkeypatch.setattr("conda.base.context.user_rc_path", user_condarc)
    reset_context()

    # Test factory method
    config = ConfigurationFile.from_user_condarc()
    assert config.path == user_condarc
    assert config.content == {"channels": ["conda-forge"]}


def test_config_file_from_system_condarc(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    """Test ConfigurationFile.from_system_condarc() factory method."""
    # Create a temporary system condarc
    sys_condarc = tmp_path / "system_condarc"
    sys_condarc.write_text("auto_update_conda: false\n")

    # Mock the sys_rc_path
    monkeypatch.setattr("conda.base.context.sys_rc_path", sys_condarc)
    reset_context()

    # Test factory method
    config = ConfigurationFile.from_system_condarc()
    assert config.path == sys_condarc
    assert config.content == {"auto_update_conda": False}


def test_config_file_from_env_condarc(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    """Test ConfigurationFile.from_env_condarc() factory method."""
    # Create a temporary environment with .condarc
    env_prefix = tmp_path / "myenv"
    env_prefix.mkdir()
    env_condarc = env_prefix / ".condarc"
    env_condarc.write_text("pip_interop_enabled: true\n")

    # Test with explicit prefix
    config = ConfigurationFile.from_env_condarc(prefix=env_prefix)
    assert config.path == env_condarc
    assert config.content == {"pip_interop_enabled": True}

    # Test with CONDA_PREFIX environment variable
    monkeypatch.setenv("CONDA_PREFIX", str(env_prefix))
    config2 = ConfigurationFile.from_env_condarc()
    assert config2.path == env_condarc
    assert config2.content == {"pip_interop_enabled": True}


def test_config_file_context_manager(tmp_path: Path) -> None:
    """Test ConfigurationFile as context manager for atomic writes."""
    config_path = tmp_path / ".condarc"

    # Test that changes are written on successful exit
    with ConfigurationFile(path=config_path, content={}) as config:
        config.content["channels"] = ["defaults", "conda-forge"]
        config.content["auto_update_conda"] = False

    # Verify file was written
    assert config_path.exists()
    written_content = config_path.read_text()
    assert "channels:" in written_content
    assert "defaults" in written_content
    assert "conda-forge" in written_content
    assert "auto_update_conda: false" in written_content


def test_config_file_context_manager_exception(tmp_path: Path) -> None:
    """Test that ConfigurationFile context manager doesn't write on exception."""
    config_path = tmp_path / ".condarc"

    # Test that changes are NOT written if exception occurs
    try:
        with ConfigurationFile(path=config_path, content={}) as config:
            config.content["channels"] = ["defaults"]
            raise ValueError("Test exception")
    except ValueError:
        pass

    # Verify file was NOT written (because exception occurred)
    assert not config_path.exists()


@pytest.mark.parametrize(
    ("operation", "message"),
    [
        ("fsync", "simulated write failure"),
        ("replace", "simulated replacement failure"),
    ],
)
def test_config_write_failure_preserves_file(
    tmp_path: Path, mocker: MockerFixture, operation: str, message: str
) -> None:
    path = tmp_path / ".condarc"
    original = "changeps1: true\n"
    path.write_text(original)
    config = ConfigurationFile(path)
    config.set_key("changeps1", False)
    mocker.patch(f"os.{operation}", side_effect=OSError(message))

    with pytest.raises(conda.exceptions.CondaError, match=message):
        config.write()

    assert path.read_text() == original
    assert set(tmp_path.iterdir()) == {path, tmp_path / ".condarc.lock"}


@pytest.mark.parametrize("initial", [None, "changeps1: true\n"])
def test_config_write_rejects_changed_source(
    tmp_path: Path, initial: str | None
) -> None:
    path = tmp_path / ".condarc"
    if initial is not None:
        path.write_text(initial)
    config = ConfigurationFile(path)
    config.set_key("changeps1", False)
    changed = "changeps1: true\nalways_yes: false\n"
    path.write_text(changed)

    with pytest.raises(conda.exceptions.CondaError, match="file changed after reading"):
        config.write()

    assert path.read_text() == changed
    assert list(tmp_path.iterdir()) == [path]


def test_config_write_rejects_change_during_write(
    tmp_path: Path, mocker: MockerFixture
) -> None:
    path = tmp_path / ".condarc"
    path.write_text("changeps1: true\n")
    config = ConfigurationFile(path)
    config.set_key("changeps1", False)
    changed = "changeps1: true\nalways_yes: false\n"
    mocker.patch("os.fsync", side_effect=lambda fd: path.write_text(changed))

    with pytest.raises(conda.exceptions.CondaError, match="file changed while writing"):
        config.write()

    assert path.read_text() == changed
    assert set(tmp_path.iterdir()) == {path, tmp_path / ".condarc.lock"}


@pytest.mark.skipif(on_win, reason="POSIX file permissions")
def test_config_write_preserves_permissions(tmp_path: Path) -> None:
    path = tmp_path / ".condarc"
    path.write_text("changeps1: true\n")
    path.chmod(0o640)
    config = ConfigurationFile(path)
    config.set_key("changeps1", False)
    config.write()

    assert S_IMODE(path.stat().st_mode) == 0o640
    assert path.read_text() == "changeps1: false\n"


@pytest.mark.skipif(not on_mac, reason="macOS file ACLs")
def test_config_write_preserves_macos_acl(
    tmp_path: Path, mocker: MockerFixture
) -> None:
    from subprocess import run

    from conda.common._os.osx import copy_acl

    path = tmp_path / ".condarc"
    path.write_text("changeps1: true\n")
    run(
        ["/bin/chmod", "+a", "user:nobody deny read", path],
        check=True,
        capture_output=True,
        text=True,
    )
    before = run(
        ["/bin/ls", "-lde", path],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()[1:]
    config = ConfigurationFile(path)
    config.set_key("changeps1", False)
    copy_calls = 0

    def copy_and_check_mode(source_fd: int, destination_fd: int) -> None:
        nonlocal copy_calls
        copy_calls += 1
        assert S_IMODE(os.fstat(destination_fd).st_mode) == 0
        copy_acl(source_fd, destination_fd)

    def check_candidate_acl(fd: int) -> None:
        candidate = next(tmp_path.glob("*.tmp"))
        staged = run(
            ["/bin/ls", "-lde", candidate],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.splitlines()[1:]
        assert staged == before

    mocker.patch("conda.common._os.osx.copy_acl", side_effect=copy_and_check_mode)
    mocker.patch("os.fsync", side_effect=check_candidate_acl)
    config.write()

    after = run(
        ["/bin/ls", "-lde", path],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()[1:]
    assert copy_calls == 1
    assert after == before


@pytest.mark.skipif(not on_mac, reason="macOS file ACLs")
def test_config_write_macos_acl_failure_preserves_file(
    tmp_path: Path, mocker: MockerFixture
) -> None:
    path = tmp_path / ".condarc"
    original = "changeps1: true\n"
    path.write_text(original)
    config = ConfigurationFile(path)
    config.set_key("changeps1", False)
    mocker.patch(
        "conda.common._os.osx.copy_acl", side_effect=OSError("simulated ACL failure")
    )

    with pytest.raises(conda.exceptions.CondaError, match="simulated ACL failure"):
        config.write()

    assert path.read_text() == original
    assert set(tmp_path.iterdir()) == {path, tmp_path / ".condarc.lock"}


@pytest.mark.skipif(not on_mac, reason="macOS file ACLs")
@pytest.mark.parametrize("mutation", ("acl", "replacement"))
def test_config_write_rejects_macos_security_change(
    tmp_path: Path, mocker: MockerFixture, mutation: str
) -> None:
    from subprocess import run

    from conda.common._os.osx import copy_acl

    path = tmp_path / ".condarc"
    original = "changeps1: true\n"
    path.write_text(original)
    config = ConfigurationFile(path)
    config.set_key("changeps1", False)

    def change_after_copy(source_fd: int, destination_fd: int) -> None:
        copy_acl(source_fd, destination_fd)
        if mutation == "acl":
            run(
                ["/bin/chmod", "+a", "user:nobody deny read", path],
                check=True,
                capture_output=True,
                text=True,
            )
        else:
            replacement = tmp_path / "replacement"
            replacement.write_text(original)
            os.replace(replacement, path)

    mocker.patch("conda.common._os.osx.copy_acl", side_effect=change_after_copy)

    with pytest.raises(conda.exceptions.CondaError, match="file changed while writing"):
        config.write()

    assert path.read_text() == original
    assert set(tmp_path.iterdir()) == {path, tmp_path / ".condarc.lock"}


@pytest.mark.skipif(
    on_win or os.geteuid() == 0, reason="POSIX unprivileged permissions"
)
def test_config_write_respects_read_only_file(tmp_path: Path) -> None:
    path = tmp_path / ".condarc"
    original = "changeps1: true\n"
    path.write_text(original)
    path.chmod(0o400)
    config = ConfigurationFile(path)
    config.set_key("changeps1", False)

    with pytest.raises(
        conda.exceptions.CondaError, match="Cannot write to condarc file"
    ):
        config.write()

    assert path.read_text() == original
    assert set(tmp_path.iterdir()) == {path, tmp_path / ".condarc.lock"}


@pytest.mark.skipif(on_win, reason="symlink privilege required")
def test_config_write_preserves_symlink(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.write_text("changeps1: true\n")
    path = tmp_path / ".condarc"
    path.symlink_to(target.name)
    config = ConfigurationFile(path)
    config.set_key("changeps1", False)
    config.write()

    assert path.is_symlink()
    assert target.read_text() == "changeps1: false\n"


def test_config_write_refreshes_read_state(tmp_path: Path) -> None:
    path = tmp_path / ".condarc"
    config = ConfigurationFile(path)
    config.set_key("changeps1", False)
    config.write()
    config.set_key("always_yes", False)
    config.write()

    assert path.read_text() == "changeps1: false\nalways_yes: false\n"


@pytest.mark.skipif(on_win, reason="POSIX file permissions")
def test_config_new_file_honors_umask(tmp_path: Path) -> None:
    reference = tmp_path / "reference"
    reference.write_text("")
    path = tmp_path / ".condarc"
    config = ConfigurationFile(path)
    config.set_key("changeps1", False)
    config.write()

    assert S_IMODE(path.stat().st_mode) == S_IMODE(reference.stat().st_mode)


def test_config_write_other_path(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.write_text("changeps1: true\n")
    path = tmp_path / ".condarc"
    config = ConfigurationFile(path)
    config.read(source)
    config.set_key("always_yes", False)
    config.write()

    assert path.read_text() == "changeps1: true\nalways_yes: false\n"
    assert source.read_text() == "changeps1: true\n"


@pytest.mark.parametrize("changeps1", [True, False])
def test_config_write_rejects_same_content_replacement(
    tmp_path: Path, changeps1: bool
) -> None:
    path = tmp_path / ".condarc"
    original = "changeps1: true\n"
    path.write_text(original)
    config = ConfigurationFile(path)
    config.set_key("changeps1", changeps1)
    replacement = tmp_path / "replacement"
    replacement.write_text(original)
    os.replace(replacement, path)

    with pytest.raises(conda.exceptions.CondaError, match="file changed after reading"):
        config.write()

    assert path.read_text() == original
    assert set(tmp_path.iterdir()) == {path}


@pytest.mark.skipif(on_win, reason="POSIX file permissions")
def test_config_write_rejects_permissions_changed_after_read(tmp_path: Path) -> None:
    path = tmp_path / ".condarc"
    path.write_text("changeps1: true\n")
    path.chmod(0o600)
    config = ConfigurationFile(path)
    config.set_key("changeps1", False)
    path.chmod(0o640)

    with pytest.raises(conda.exceptions.CondaError, match="file changed after reading"):
        config.write()

    assert path.read_text() == "changeps1: true\n"
    assert S_IMODE(path.stat().st_mode) == 0o640


@pytest.mark.skipif(on_win, reason="Windows ctime is creation time on Python 3.10")
def test_config_write_rejects_restored_contents_and_mtime(tmp_path: Path) -> None:
    path = tmp_path / ".condarc"
    original = "changeps1: true\n"
    path.write_text(original)
    config = ConfigurationFile(path)
    config.set_key("changeps1", False)
    before = path.stat()
    path.write_text("changeps1: false\n")
    path.write_text(original)
    os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
    if path.stat().st_ctime_ns == before.st_ctime_ns:
        pytest.skip("The filesystem did not record a distinct metadata change time")

    with pytest.raises(conda.exceptions.CondaError, match="file changed after reading"):
        config.write()

    assert path.read_text() == original


@pytest.mark.skipif(on_win, reason="symlink privilege required")
def test_config_write_rejects_retargeted_symlink(tmp_path: Path) -> None:
    original = "changeps1: true\n"
    target = tmp_path / "target"
    target.write_text(original)
    other = tmp_path / "other"
    other.write_text(original)
    path = tmp_path / ".condarc"
    path.symlink_to(target.name)
    config = ConfigurationFile(path)
    config.set_key("changeps1", False)
    path.unlink()
    path.symlink_to(other.name)

    with pytest.raises(conda.exceptions.CondaError, match="file changed after reading"):
        config.write()

    assert path.resolve() == other
    assert target.read_text() == other.read_text() == original


@pytest.mark.skipif(on_win, reason="symlink privilege required")
@pytest.mark.parametrize("same_target", [True, False])
def test_config_write_checks_read_state_through_symlink(
    tmp_path: Path, same_target: bool
) -> None:
    source = tmp_path / "source"
    source.write_text("changeps1: true\n")
    config = ConfigurationFile(source)
    config.set_key("changeps1", False)
    changed = "changeps1: true\nalways_yes: true\n"
    source.write_text(changed)
    target = source if same_target else tmp_path / "other"
    if not same_target:
        target.write_text("always_yes: false\n")
    alias = tmp_path / "alias"
    alias.symlink_to(target.name)

    if same_target:
        with pytest.raises(
            conda.exceptions.CondaError, match="file changed after reading"
        ):
            config.write(alias)
    else:
        config.write(alias)
        assert target.read_text() == "changeps1: false\n"

    assert source.read_text() == changed
    assert alias.is_symlink()


def test_config_read_rejects_change_during_read(
    tmp_path: Path, mocker: MockerFixture
) -> None:
    path = tmp_path / ".condarc"
    path.write_text("changeps1: true\n")
    config = ConfigurationFile(path)
    fstat = os.fstat
    changed = False

    def change_after_stat(fd: int) -> os.stat_result:
        nonlocal changed
        result = fstat(fd)
        if not changed:
            changed = True
            path.write_text("changeps1: false\nalways_yes: true\n")
        return result

    mocker.patch("os.fstat", side_effect=change_after_stat)
    with pytest.raises(conda.exceptions.CondaError, match="file changed while reading"):
        config.read()

    assert config._read_state is None
    assert config._content is None


def test_config_write_rejects_same_content_replacement_during_write(
    tmp_path: Path, mocker: MockerFixture
) -> None:
    path = tmp_path / ".condarc"
    original = "changeps1: true\n"
    path.write_text(original)
    config = ConfigurationFile(path)
    config.set_key("changeps1", False)

    def replace_source(fd: int) -> None:
        replacement = tmp_path / "replacement"
        replacement.write_text(original)
        os.replace(replacement, path)

    mocker.patch("os.fsync", side_effect=replace_source)
    with pytest.raises(conda.exceptions.CondaError, match="file changed while writing"):
        config.write()

    assert path.read_text() == original
    assert set(tmp_path.iterdir()) == {path, tmp_path / ".condarc.lock"}


@pytest.mark.skipif(on_win, reason="Replacing an open temporary file requires POSIX")
def test_config_write_leaves_replaced_temporary_file(
    tmp_path: Path, mocker: MockerFixture
) -> None:
    path = tmp_path / ".condarc"
    original = "changeps1: true\n"
    path.write_text(original)
    config = ConfigurationFile(path)
    config.set_key("changeps1", False)

    def replace_temporary(fd: int) -> None:
        candidate = next(tmp_path.glob("*.tmp"))
        candidate.unlink()
        candidate.write_text("another writer's file\n")

    mocker.patch("os.fsync", side_effect=replace_temporary)
    with pytest.raises(conda.exceptions.CondaError, match="file changed while writing"):
        config.write()

    assert path.read_text() == original
    assert next(tmp_path.glob("*.tmp")).read_text() == "another writer's file\n"


@pytest.mark.parametrize(
    "later_text", ["changeps1: false\n", "changeps1: false\nalways_yes: true\n"]
)
def test_config_write_does_not_adopt_later_replacement(
    tmp_path: Path, mocker: MockerFixture, later_text: str
) -> None:
    path = tmp_path / ".condarc"
    path.write_text("changeps1: true\n")
    config = ConfigurationFile(path)
    config.set_key("changeps1", False)
    replace = os.replace

    def replace_again(source: Path, destination: Path) -> None:
        replace(source, destination)
        later = tmp_path / "later"
        later.write_text(later_text)
        replace(later, destination)

    mocker.patch("os.replace", side_effect=replace_again)
    config.write()
    config.set_key("always_yes", False)
    with pytest.raises(conda.exceptions.CondaError, match="file changed after reading"):
        config.write()

    assert path.read_text() == later_text


@pytest.mark.skipif(on_win, reason="POSIX directory permissions")
def test_config_write_noop_does_not_need_writable_directory(tmp_path: Path) -> None:
    path = tmp_path / ".condarc"
    path.write_text("changeps1: true\n")
    config = ConfigurationFile(path)
    config.read()
    tmp_path.chmod(0o500)
    try:
        config.write()
        assert set(tmp_path.iterdir()) == {path}
    finally:
        tmp_path.chmod(0o700)


def test_config_write_serializes_threads(tmp_path: Path, mocker: MockerFixture) -> None:
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event

    from conda.cli import condarc

    path = tmp_path / ".condarc"
    path.write_text("changeps1: true\n")
    first = ConfigurationFile(path)
    first.set_key("changeps1", False)
    second = ConfigurationFile(path)
    second.set_key("always_yes", True)
    replacing = Event()
    second_waiting = Event()
    write_lock = condarc._write_lock
    replace = os.replace

    class ObservedLock:
        def __enter__(self):
            if replacing.is_set():
                second_waiting.set()
            return write_lock.__enter__()

        def __exit__(self, *args):
            return write_lock.__exit__(*args)

    def wait_for_second_writer(source: Path, destination: Path) -> None:
        replacing.set()
        assert second_waiting.wait(10)
        replace(source, destination)

    mocker.patch.object(condarc, "_write_lock", ObservedLock())
    mocker.patch("os.replace", side_effect=wait_for_second_writer)
    with ThreadPoolExecutor(max_workers=2) as executor:
        first_write = executor.submit(first.write)
        assert replacing.wait(10)
        second_write = executor.submit(second.write)
        first_write.result(timeout=10)
        with pytest.raises(
            conda.exceptions.CondaError, match="file changed while waiting to write"
        ):
            second_write.result(timeout=10)

    assert path.read_text() == "changeps1: false\n"


@pytest.mark.skipif(not hasattr(os, "fork"), reason="requires fork")
def test_config_write_after_fork_with_lock_held_by_thread(tmp_path: Path) -> None:
    import signal
    from multiprocessing import get_context
    from threading import Event, Thread

    from conda.cli import condarc

    path = tmp_path / ".condarc"
    held = Event()
    release = Event()

    def hold_lock() -> None:
        with condarc._write_lock:
            held.set()
            release.wait(20)

    multiprocessing = get_context("fork")
    parent, child = multiprocessing.Pipe(duplex=False)

    def write_in_child() -> None:
        signal.alarm(5)
        try:
            ConfigurationFile(path, content={"changeps1": False}).write()
            child.send("written")
        except Exception as error:
            child.send(type(error).__name__)
        finally:
            child.close()

    thread = Thread(target=hold_lock)
    process = multiprocessing.Process(target=write_in_child)
    thread.start()
    try:
        assert held.wait(5)
        process.start()
        assert parent.poll(10)
        assert parent.recv() == "written"
        process.join(5)
        assert process.exitcode == 0
        assert path.read_text() == "changeps1: false\n"
    finally:
        release.set()
        thread.join(5)
        if process.is_alive():
            process.terminate()
            process.join(5)
        parent.close()
        child.close()


def test_config_write_accepts_windows_timestamps_finalized_on_close(
    tmp_path: Path, mocker: MockerFixture
) -> None:
    from types import SimpleNamespace

    from conda.cli import condarc

    path = tmp_path / ".condarc"
    path.write_text("changeps1: true\n")
    config = ConfigurationFile(path)
    config.set_key("changeps1", False)
    fsync = os.fsync
    fstat = os.fstat
    pending_fd = None
    changed = 0

    def sync_with_pending_timestamps(fd: int) -> None:
        nonlocal pending_fd
        fsync(fd)
        pending_fd = fd

    def stat_with_pending_timestamps(fd: int):
        nonlocal pending_fd, changed
        metadata = fstat(fd)
        if fd != pending_fd:
            return metadata
        pending_fd = None
        changed += 1
        pending = SimpleNamespace(
            **{
                name: getattr(metadata, name)
                for name in dir(metadata)
                if name.startswith("st_")
            }
        )
        pending.st_mtime_ns -= 1
        pending.st_ctime_ns -= 1
        return pending

    mocker.patch.object(condarc, "on_win", True)
    mocker.patch.object(condarc, "on_mac", False)
    mocker.patch("os.fsync", side_effect=sync_with_pending_timestamps)
    mocker.patch("os.fstat", side_effect=stat_with_pending_timestamps)
    config.write()
    config.set_key("always_yes", False)
    config.write()

    assert changed == 2
    assert path.read_text() == "changeps1: false\nalways_yes: false\n"
