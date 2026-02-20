# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from os.path import isdir
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest

from conda.base.constants import PREFIX_FROZEN_FILE
from conda.base.context import context
from conda.cli.main_info import (
    get_info_components,
    iter_info_components,
)
from conda.common.path import paths_equal
from conda.core.envs_manager import list_all_known_prefixes
from conda.core.prefix_data import PrefixData
from conda.exceptions import ArgumentError
from conda.plugins.reporter_backends.console import ConsoleReporterRenderer

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from conda.testing.fixtures import CondaCLIFixture, TmpEnvFixture


BASE_KEYS = {"root_prefix"}
UNSAFE_CHANNELS_KEYS = {"channels"}
ENVS_KEYS = {"envs"}
SYSTEM_KEYS = {
    "sys.version",
    "sys.prefix",
    "sys.executable",
    "conda_location",
    "env_vars",
    "site_dirs",
}
DETAIL_KEYS = {
    "platform",
    "conda_version",
    "envs_dirs",
    "pkgs_dirs",
    "channels",
    "config_files",
    "offline",
    "solver",
}


# conda info --base [--json]
def test_info_base(conda_cli: CondaCLIFixture) -> None:
    stdout, stderr, err = conda_cli("info", "--base")
    assert paths_equal(stdout.strip(), context.root_prefix)
    assert not stderr
    assert not err

    stdout, stderr, err = conda_cli("info", "--base", "--json")
    parsed = json.loads(stdout.strip())
    assert paths_equal(parsed["root_prefix"], context.root_prefix)
    assert not stderr
    assert not err


# conda info --unsafe-channels [--json]
def test_info_unsafe_channels(
    conda_cli: CondaCLIFixture,
    mocker: MockerFixture,
) -> None:
    channels = [
        "https://conda.anaconda.org/t/tk-123/a/b/c",
        "another-channel",
    ]
    mocker.patch(
        "conda.base.context.Context.channels",
        new_callable=mocker.PropertyMock,
        return_value=channels,
    )
    assert context.channels == channels

    stdout, stderr, err = conda_cli("info", "--unsafe-channels")
    assert stdout.strip() == "\n".join(channels)
    assert not stderr
    assert not err

    stdout, stderr, err = conda_cli("info", "--unsafe-channels", "--json")
    parsed = json.loads(stdout.strip())
    assert parsed["channels"] == channels
    assert not stderr
    assert not err


# conda info --envs [--json]
def test_info_envs(conda_cli: CondaCLIFixture):
    prefixes = list_all_known_prefixes()

    stdout, stderr, err = conda_cli("info", "--envs")
    assert stdout == ConsoleReporterRenderer.envs_list(prefixes)
    assert not stderr
    assert not err

    stdout, stderr, err = conda_cli("info", "--envs", "--json")
    parsed = json.loads(stdout.strip())
    assert parsed["envs"] == prefixes
    assert not stderr
    assert not err


def test_info_envs_frozen(conda_cli: CondaCLIFixture, tmp_env, test_recipes_channel):
    with tmp_env() as prefix:
        Path(prefix, PREFIX_FROZEN_FILE).touch()
        prefixes = list_all_known_prefixes()

        stdout, stderr, err = conda_cli("info", "--envs")
        assert stdout == ConsoleReporterRenderer.envs_list(prefixes)
        assert " + " in stdout
        assert not stderr
        assert not err


# conda info --system [--json]
def test_info_system(conda_cli: CondaCLIFixture):
    stdout, stderr, err = conda_cli("info", "--system")
    assert "sys.version:" in stdout
    assert "sys.prefix:" in stdout
    assert "sys.executable:" in stdout
    assert "conda location:" in stdout
    assert "conda-build:" in stdout
    assert "PATH:" in stdout
    assert "user site dirs:" in stdout
    assert not stderr
    assert not err

    stdout, stderr, err = conda_cli("info", "--system", "--json")
    parsed = json.loads(stdout.strip())
    assert SYSTEM_KEYS <= set(parsed.keys())
    assert not stderr
    assert not err


# conda info [--json]
def test_info_detail(conda_cli: CondaCLIFixture):
    stdout, stderr, err = conda_cli("info")
    assert "platform" in stdout
    assert "conda version" in stdout
    assert "envs directories" in stdout
    assert "package cache" in stdout
    assert "channel URLs" in stdout
    assert "config file" in stdout
    assert "offline mode" in stdout
    assert "solver" in stdout
    assert not stderr
    assert not err

    stdout, stderr, err = conda_cli("info", "--json")
    parsed = json.loads(stdout.strip())
    assert DETAIL_KEYS <= set(parsed.keys())
    assert not stderr
    assert not err


# conda info --all [--json]
def test_info_all(conda_cli: CondaCLIFixture):
    stdout_detail, _, _ = conda_cli("info")
    stdout_envs, _, _ = conda_cli("info", "--envs")
    stdout_system, _, _ = conda_cli("info", "--system")

    stdout, stderr, err = conda_cli("info", "--all")
    assert stdout == (stdout_detail + stdout_envs + stdout_system)
    assert not stderr
    assert not err

    stdout, stderr, err = conda_cli("info", "--all", "--json")
    parsed = json.loads(stdout.strip())
    assert {*DETAIL_KEYS, *ENVS_KEYS, *SYSTEM_KEYS} <= set(parsed.keys())
    assert not stderr
    assert not err


# conda info --json
def test_info_json(conda_cli: CondaCLIFixture):
    stdout, _, _ = conda_cli("info", "--json")
    parsed = json.loads(stdout.strip())
    assert isinstance(parsed, dict)

    # assert all keys are present
    assert {
        "channels",
        "conda_version",
        "default_prefix",
        "envs",
        "envs_details",
        "envs_dirs",
        "pkgs_dirs",
        "platform",
        "python_version",
        "rc_path",
        "root_prefix",
        "root_writable",
        "solver",
    } <= set(parsed)

    # assert all envs_details keys are present
    keys_and_types = {
        "name": str,
        "created": (str, type(None)),
        "last_modified": str,
        "active": bool,
        "base": bool,
        "frozen": bool,
        "writable": bool,
    }
    for prefix, details in parsed["envs_details"].items():
        assert isinstance(prefix, str)
        assert set(keys_and_types.keys()) == set(details.keys())
        for key, type_ in keys_and_types.items():
            assert isinstance(details[key], type_)


# conda info --envs --json
def test_info_envs_json(conda_cli: CondaCLIFixture):
    stdout, _, _ = conda_cli("info", "--envs", "--json")
    parsed = json.loads(stdout.strip())
    assert isinstance(parsed, dict)

    # assert only 'envs' is present
    assert {"envs", "envs_details"} == set(parsed)
    assert parsed["envs"]
    assert isinstance(parsed["envs"], list)
    assert isinstance(parsed["envs"][0], str)
    assert isdir(parsed["envs"][0])
    assert parsed["envs_details"]
    assert isinstance(parsed["envs_details"], dict)
    first_env = next(iter(parsed["envs_details"].keys()))
    assert isdir(first_env)
    first_envs_details = parsed["envs_details"][first_env]
    assert isinstance(first_envs_details, dict)
    assert "size" not in first_envs_details


def test_info_envs_size(conda_cli: CondaCLIFixture):
    stdout, stderr, err = conda_cli("info", "--envs", "--size")
    assert not stderr
    assert not err

    lines = stdout.strip().split("\n")
    non_comment_lines = [line for line in lines if line and not line.startswith("#")]

    # regex to match: <any prefix stuff> <number> <unit> <path>
    # The path is at the end of the line.
    pattern = re.compile(
        r"\s+(?P<size>\d+(\.\d+)?)\s+(?P<unit>B|KB|MB|GB)\s+(?P<path>.*)$"
    )

    for line in non_comment_lines:
        match = pattern.search(line)
        assert match, f"Line did not match size pattern: {line}"
        assert match.group("unit") in ["B", "KB", "MB", "GB"]


def test_info_envs_size_json(conda_cli: CondaCLIFixture):
    stdout, stderr, err = conda_cli("info", "--envs", "--size", "--json")
    assert not stderr
    assert not err

    parsed = json.loads(stdout.strip())
    assert isinstance(parsed, dict)
    assert "envs_details" in parsed

    for _, details in parsed["envs_details"].items():
        assert "size" in details
        assert isinstance(details["size"], int)
        assert details["size"] >= 0


# conda info --license
def test_info_license(conda_cli: CondaCLIFixture):
    with pytest.deprecated_call():
        conda_cli("info", "--license")


# conda info --root
def test_info_root(conda_cli: CondaCLIFixture):
    with pytest.deprecated_call():
        conda_cli("info", "--root")


def test_iter_info_components() -> None:
    components = iter_info_components(
        args=SimpleNamespace(
            base=True,
            unsafe_channels=True,
            all=True,
            envs=True,
            system=True,
        ),
        context=SimpleNamespace(json=False),
    )
    assert isinstance(components, Iterable)
    assert tuple(components) == ("base", "channels", "envs", "envs_details", "system")


def test_get_info_components() -> None:
    with pytest.deprecated_call():
        components = get_info_components(
            args=SimpleNamespace(
                base=True,
                unsafe_channels=True,
                all=True,
                envs=True,
                system=True,
            ),
            context=SimpleNamespace(json=False),
        )
    assert isinstance(components, set)
    assert components == {"base", "channels", "envs", "envs_details", "system"}


def test_compute_prefix_size(tmp_env: TmpEnvFixture):
    with tmp_env("ca-certificates") as prefix:
        prefix_data = PrefixData(prefix)
        size = prefix_data.size()
        assert size > 0


def test_compute_prefix_size_empty_env(tmp_env: TmpEnvFixture):
    with tmp_env() as prefix:
        prefix_data = PrefixData(prefix)
        size = prefix_data.size()
        assert size == 0


def test_info_size_without_envs(conda_cli: CondaCLIFixture):
    with pytest.raises(ArgumentError, match="--size can only be used with --envs"):
        conda_cli("info", "--size")
