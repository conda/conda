# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import json
from importlib import import_module
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from conda.plugins.manager import CondaPluginManager
    from conda.testing.fixtures import CondaCLIFixture


@pytest.fixture
def plugin_manager_with_plugins_command(
    plugin_manager: CondaPluginManager,
) -> CondaPluginManager:
    plugin_manager.load_plugins(import_module("conda.plugins.subcommands.plugins"))
    return plugin_manager


@pytest.fixture
def plugin_manager_with_test_plugin(
    plugin_manager_with_plugins_command: CondaPluginManager,
) -> CondaPluginManager:
    assert (
        plugin_manager_with_plugins_command.load_entrypoints(
            "test_plugin",
            "success",
        )
        == 1
    )
    return plugin_manager_with_plugins_command


def test_plugins_help(
    plugin_manager_with_plugins_command: CondaPluginManager,
    conda_cli: CondaCLIFixture,
):
    out, err, exc = conda_cli("plugins", "--help", raises=SystemExit)

    assert exc.value.code == 0
    assert "list" in out
    assert not err


def test_plugins_list_help(
    plugin_manager_with_plugins_command: CondaPluginManager,
    conda_cli: CondaCLIFixture,
):
    out, err, exc = conda_cli("plugins", "list", "--help", raises=SystemExit)

    assert exc.value.code == 0
    assert "List installed conda plugins." in out
    assert not err


def test_plugins_list_empty(
    plugin_manager_with_plugins_command: CondaPluginManager,
    conda_cli: CondaCLIFixture,
):
    out, err, code = conda_cli("plugins", "list")

    assert code == 0, f"conda plugins list failed ({code}): {err}"
    assert out == "No plugins installed.\n"
    assert not err


def test_plugins_list_table(
    plugin_manager_with_test_plugin: CondaPluginManager,
    conda_cli: CondaCLIFixture,
):
    out, err, code = conda_cli("plugins", "list")

    assert code == 0, f"conda plugins list failed ({code}): {err}"
    assert "Name" in out
    assert "Version" in out
    assert "Status" in out
    assert "Hooks" in out
    assert "conda-test-plugin" in out
    assert "active" in out
    assert "solvers" in out
    assert not err


def test_plugins_list_disabled(
    plugin_manager_with_test_plugin: CondaPluginManager,
    conda_cli: CondaCLIFixture,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("CONDA_NO_PLUGINS", "true")

    out, err, code = conda_cli("plugins", "list")

    assert code == 0, f"conda plugins list failed ({code}): {err}"
    assert "conda-test-plugin" in out
    assert "disabled" in out
    assert "solvers" in out
    assert not err


def test_plugins_list_json(
    plugin_manager_with_test_plugin: CondaPluginManager,
    conda_cli: CondaCLIFixture,
):
    out, err, code = conda_cli("plugins", "list", "--json")

    assert code == 0, f"conda plugins list --json failed ({code}): {err}"
    data = json.loads(out)
    test_plugin = next(
        plugin for plugin in data if plugin["name"] == "conda-test-plugin"
    )

    assert test_plugin == {
        "name": "conda-test-plugin",
        "version": "1.0",
        "canonical_name": "test_plugin.success",
        "status": "active",
        "hooks": ["solvers"],
    }
    assert not err
