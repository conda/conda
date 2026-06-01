# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Tests for `conda create` help text."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from conda.cli.main_create import epilog as create_epilog
from conda.plugins import hookimpl
from conda.plugins.types import (
    CondaEnvironmentSpecifier,
    EnvironmentFormat,
    EnvironmentSpecBase,
)

if TYPE_CHECKING:
    from conda.plugins.manager import CondaPluginManager
    from conda.testing.fixtures import CondaCLIFixture


class DummyEnvSpecPlugin:
    @hookimpl
    def conda_environment_specifiers(self):
        yield CondaEnvironmentSpecifier(
            name="dummy-spec",
            environment_spec=EnvironmentSpecBase,
            aliases=("spec",),
            environment_format=EnvironmentFormat.environment,
        )


class DummyLockfilePlugin:
    @hookimpl
    def conda_environment_specifiers(self):
        yield CondaEnvironmentSpecifier(
            name="dummy-lock",
            environment_spec=EnvironmentSpecBase,
            aliases=("lock",),
            environment_format=EnvironmentFormat.lockfile,
        )


@pytest.mark.parametrize(
    "spec_plugin,lockfile_plugin",
    [
        pytest.param(False, False, id="no plugins"),
        pytest.param(True, False, id="spec plugin only"),
        pytest.param(False, True, id="lockfile plugin only"),
        pytest.param(True, True, id="all plugins"),
    ],
)
def test_epilog(
    plugin_manager_with_reporter_backends: CondaPluginManager,
    subtests,
    spec_plugin: bool,
    lockfile_plugin: bool,
) -> None:
    """``conda create --help`` renders examples and format epilog using the registered plugins."""
    # register dummy plugins
    if spec_plugin:
        plugin_manager_with_reporter_backends.register(DummyEnvSpecPlugin())
    if lockfile_plugin:
        plugin_manager_with_reporter_backends.register(DummyLockfilePlugin())

    # check help contains expected text
    epilog = create_epilog()
    for expected, line in (
        (True, "Examples:"),
        (True, "Create from package specs:"),
        (True, "conda create -n myenv python=3.12 numpy"),
        (True, "Create from an environment spec (solved at install time):"),
        (True, "conda create -n myenv --file environment.yml"),
        (True, "Create from a lockfile (no solve, exact reproduction):"),
        (True, "conda create -n myenv --file explicit.txt"),
        (True, "Clone an existing environment:"),
        (True, "conda create -n env2 --clone env1"),
        (spec_plugin or lockfile_plugin, "Available input formats:"),
        (spec_plugin, "Environment specs:"),
        (spec_plugin, "- dummy-spec (aliases: spec)"),
        (lockfile_plugin, "Lockfiles:"),
        (lockfile_plugin, "- dummy-lock (aliases: lock)"),
    ):
        with subtests.test(line):
            assert (line in epilog) is expected, epilog


def test_create_help(conda_cli: CondaCLIFixture) -> None:
    """``conda create --help`` renders the epilog."""
    stdout, _, _ = conda_cli("create", "--help", raises=SystemExit)
    assert create_epilog() in stdout
