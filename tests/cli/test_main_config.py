# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from conda.base.context import context, reset_context
from conda.cli.main_config import (
    _get_key,
    _read_rc,
    _remove_item,
    _remove_key,
    _set_key,
    _write_rc,
    set_keys,
)
from conda.exceptions import CondaKeyError

if TYPE_CHECKING:
    from typing import Any, Iterable

    from pytest import MonkeyPatch

    from conda.testing import CondaCLIFixture, PathFactoryFixture


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


def test_config_set_key() -> None:
    config: dict[str, Any] = {}

    # unknown
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
    condarc = tmp_path / ".condarc"
    condarc.write_text("changeps1: false\nauto_stack: 5\n")

    assert _read_rc(path=condarc) == {"changeps1": False, "auto_stack": 5}


def test_config_write_rc(tmp_path: Path) -> None:
    condarc = tmp_path / ".condarc"

    _write_rc(condarc, {"changeps1": False, "auto_stack": 5})
    assert condarc.read_text() == "changeps1: false\nauto_stack: 5\n"


def test_config_set_keys(tmp_path: Path) -> None:
    condarc = tmp_path / ".condarc"

    set_keys(("changeps1", True), path=condarc)
    assert condarc.read_text() == "changeps1: true\n"

    set_keys(("changeps1", False), path=condarc)
    assert condarc.read_text() == "changeps1: false\n"

    set_keys(("auto_stack", 5), path=condarc)
    assert condarc.read_text() == "changeps1: false\nauto_stack: 5\n"
