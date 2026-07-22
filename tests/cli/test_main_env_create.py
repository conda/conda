# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from conda.base.context import context
from conda.cli.main_env_create import epilog as env_create_epilog
from conda.exceptions import InvalidInstaller
from conda.models.environment import Environment
from conda.plugins import hookimpl
from conda.plugins.types import CondaEnvironmentSpecifier, EnvironmentSpecBase

from .test_main_create import DummyEnvSpecPlugin, DummyLockfilePlugin

if TYPE_CHECKING:
    from pathlib import Path

    from conda.plugins.manager import CondaPluginManager
    from conda.testing.fixtures import CondaCLIFixture, PathFactoryFixture


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
    """``conda env create --help`` renders examples and format epilog using the registered plugins."""
    # register dummy plugins
    if spec_plugin:
        plugin_manager_with_reporter_backends.register(DummyEnvSpecPlugin())
    if lockfile_plugin:
        plugin_manager_with_reporter_backends.register(DummyLockfilePlugin())

    # check help contains expected text
    epilog = env_create_epilog()
    for expected, line in (
        (True, "Examples:"),
        (True, "Create from an environment spec (solved at install time):"),
        (True, "conda env create -f /path/to/environment.yml"),
        (True, "Create from a lockfile (no solve, exact reproduction):"),
        (True, "conda env create -f explicit.txt"),
        (True, "Use the default file in the current directory:"),
        (True, "conda env create"),
        (True, "conda env create -n envname"),
        (spec_plugin or lockfile_plugin, "Available input formats:"),
        (spec_plugin, "Environment specs:"),
        (spec_plugin, "- dummy-spec (aliases: spec)"),
        (lockfile_plugin, "Lockfiles:"),
        (lockfile_plugin, "- dummy-lock (aliases: lock)"),
    ):
        with subtests.test(line):
            assert (line in epilog) is expected, epilog


def test_env_create_help(conda_cli: CondaCLIFixture) -> None:
    """``conda env create --help`` renders the epilog."""
    stdout, _, _ = conda_cli("env", "create", "--help", raises=SystemExit)
    assert env_create_epilog() in stdout


class DummyExternalPackagesEnvSpecPlugin:
    class CustomEnvironmentSpec(EnvironmentSpecBase):
        def __init__(self, filename: str | None = None, **kwargs):
            self.filename = filename

        def can_handle(self):
            return True

        @property
        def env(self):
            return Environment(
                platform=context.subdir,
                external_packages={"custom": ["package"]},
            )

    @hookimpl
    def conda_environment_specifiers(self):
        yield CondaEnvironmentSpecifier(
            name="custom",
            environment_spec=self.CustomEnvironmentSpec,
            default_filenames=("invalid.yml",),
        )


def test_env_create_with_invalid_installer(
    conda_cli: CondaCLIFixture,
    tmp_path: Path,
    plugin_manager_with_exporters: CondaPluginManager,
    path_factory: PathFactoryFixture,
) -> None:
    """``conda env create`` raises an error when the installer is invalid."""
    plugin_manager_with_exporters.register(DummyExternalPackagesEnvSpecPlugin())

    (path := tmp_path / "invalid.yml").touch()
    with pytest.raises(InvalidInstaller):
        conda_cli("env", "create", f"--prefix={path_factory()}", f"--file={path}")
