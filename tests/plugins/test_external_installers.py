# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import importlib
import sys
from typing import TYPE_CHECKING

import pytest

from conda import plugins
from conda.env.installers.base import get_installer
from conda.exceptions import InvalidInstaller
from conda.plugins.types import CondaExternalInstaller

if TYPE_CHECKING:
    from conda.plugins.manager import CondaPluginManager


def _noop_install(prefix, specs, args, *_, **kwargs):
    return None


def _list_install(prefix, specs, args, *_, **kwargs):
    return ["six-1.16.0"]


def _raising_install(prefix, specs, args, *_, **kwargs):
    raise RuntimeError("resolver failed")


@pytest.fixture
def pypi_installer_plugin() -> CondaExternalInstaller:
    """A pypi external installer plugin with 'pip' as alias."""
    return CondaExternalInstaller(
        name="pypi",
        install=_noop_install,
        aliases=("pip",),
    )


@pytest.fixture
def plugin_manager_with_installer(
    pypi_installer_plugin: CondaExternalInstaller,
    plugin_manager: CondaPluginManager,
) -> CondaPluginManager:
    """Plugin manager with a pypi external installer registered."""

    class PyPIInstallerPlugin:
        @plugins.hookimpl
        def conda_external_installers(self):
            yield pypi_installer_plugin

    plugin_manager.register(PyPIInstallerPlugin())
    return plugin_manager


@pytest.mark.parametrize("query", ["pypi", "PYPI", "Pypi", "pip", "PIP", "Pip"])
def test_get_external_installer_lookup(
    plugin_manager_with_installer: CondaPluginManager,
    pypi_installer_plugin: CondaExternalInstaller,
    query: str,
):
    """Installer is found by name, alias, or case variant."""
    assert (
        plugin_manager_with_installer.get_external_installer(query)
        is pypi_installer_plugin
    )


@pytest.mark.parametrize("query", ["pypi", "pip", "PIP", "Pypi"])
def test_get_installer_resolves_plugin(
    plugin_manager_with_installer: CondaPluginManager,
    pypi_installer_plugin: CondaExternalInstaller,
    query: str,
):
    """get_installer() resolves name/alias/case to plugin."""
    assert get_installer(query) is pypi_installer_plugin


@pytest.mark.parametrize("query", ["pip", "nonexistent", "npm"])
def test_get_installer_raises_without_plugin(
    plugin_manager: CondaPluginManager,
    query: str,
):
    """get_installer() raises InvalidInstaller when no plugin handles the name."""
    with pytest.raises(InvalidInstaller):
        get_installer(query)


@pytest.mark.parametrize("query", ["pip", "pypi", "unknown"])
def test_get_external_installer_returns_none_when_missing(
    plugin_manager: CondaPluginManager,
    query: str,
):
    """Returns None when no plugin is registered."""
    assert plugin_manager.get_external_installer(query) is None


def test_get_installer_falls_back_to_builtin_module(
    plugin_manager: CondaPluginManager,
):
    """Non-pip installers fall back to built-in modules."""
    installer = get_installer("conda")
    assert hasattr(installer, "install")
    assert installer.__name__ == "conda.env.installers.conda"


def test_multiple_installers_from_one_plugin(
    plugin_manager: CondaPluginManager,
):
    """A single hook can yield multiple installers, each independently retrievable."""

    class MultiInstallerPlugin:
        @plugins.hookimpl
        def conda_external_installers(self):
            yield CondaExternalInstaller(
                name="pypi", install=_noop_install, aliases=("pip",)
            )
            yield CondaExternalInstaller(name="npm", install=_list_install)

    plugin_manager.register(MultiInstallerPlugin())

    pypi = plugin_manager.get_external_installer("pypi")
    npm = plugin_manager.get_external_installer("npm")
    assert pypi is not None
    assert npm is not None
    assert pypi.name == "pypi"
    assert npm.name == "npm"
    assert plugin_manager.get_external_installer("pip").name == "pypi"


def test_empty_aliases_only_reachable_by_name(
    plugin_manager: CondaPluginManager,
):
    """Installer with no aliases is only found by primary name."""

    class NoAliasPlugin:
        @plugins.hookimpl
        def conda_external_installers(self):
            yield CondaExternalInstaller(name="custom", install=_noop_install)

    plugin_manager.register(NoAliasPlugin())

    assert plugin_manager.get_external_installer("custom") is not None
    assert plugin_manager.get_external_installer("pip") is None
    assert plugin_manager.get_external_installer("pypi") is None


def test_install_returns_list(
    plugin_manager: CondaPluginManager,
):
    """Install callable returning a list propagates the value."""

    class ListPlugin:
        @plugins.hookimpl
        def conda_external_installers(self):
            yield CondaExternalInstaller(
                name="pypi", install=_list_install, aliases=("pip",)
            )

    plugin_manager.register(ListPlugin())
    installer = get_installer("pip")
    result = installer.install("/prefix", ["six"], None)
    assert result == ["six-1.16.0"]


def test_install_returns_none(
    plugin_manager: CondaPluginManager,
):
    """Install callable returning None doesn't crash."""

    class NonePlugin:
        @plugins.hookimpl
        def conda_external_installers(self):
            yield CondaExternalInstaller(
                name="pypi", install=_noop_install, aliases=("pip",)
            )

    plugin_manager.register(NonePlugin())
    installer = get_installer("pip")
    result = installer.install("/prefix", ["six"], None)
    assert result is None


def test_install_raises_exception(
    plugin_manager: CondaPluginManager,
):
    """Exception from install callable bubbles up."""

    class RaisingPlugin:
        @plugins.hookimpl
        def conda_external_installers(self):
            yield CondaExternalInstaller(
                name="pypi", install=_raising_install, aliases=("pip",)
            )

    plugin_manager.register(RaisingPlugin())
    installer = get_installer("pip")
    with pytest.raises(RuntimeError, match="resolver failed"):
        installer.install("/prefix", ["six"], None)


def test_pip_module_import_warns():
    """Importing the deprecated pip module emits PendingDeprecationWarning."""
    sys.modules.pop("conda.env.installers.pip", None)
    sys.modules.pop("conda.env.pip_util", None)
    with pytest.warns(PendingDeprecationWarning):
        importlib.import_module("conda.env.installers.pip")
