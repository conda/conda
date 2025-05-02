# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import pytest

from collections.abc import Iterable

from conda import plugins
from conda.exceptions import InvalidInstaller, PluginError
from conda.plugins.types import CondaInstaller, InstallerBase


class MyInstaller(InstallerBase):
    def __init__(self, **kwargs):
        pass

    def install(self, prefix, specs, *args, **kwargs) -> Iterable[str]:
        return "installing {specs} into {prefix}"


    def dry_run(self, prefix, specs, *args, **kwargs) -> Iterable[str]:
        return "DRYRUN: installing {specs} into {prefix}"


class TestInstallerPlugin:
    @plugins.hookimpl
    def conda_installers(self):
        yield CondaInstaller(
            name="test_installer",
            types=["test", "othertype"],
            installer=MyInstaller,
        )


class SecondTestInstallerPlugin:
    @plugins.hookimpl
    def conda_installers(self):
        yield CondaInstaller(
            name="second_test_installer",
            types=["test"],
            installer=MyInstaller,
        )


@pytest.fixture()
def dummy_test_installer_plugin(plugin_manager):
    plg = TestInstallerPlugin()
    plugin_manager.register(plg)
    return plugin_manager


@pytest.fixture()
def dummy_second_test_installer_plugin(plugin_manager):
    plg = SecondTestInstallerPlugin()
    plugin_manager.register(plg)
    return plugin_manager


def test_installer_is_registered(dummy_test_installer_plugin):
    """
    Ensures that our dummy random installer plugin has been registered.
    """
    backend = dummy_test_installer_plugin.get_installer("test")
    assert backend.name == "test_installer"

    backend = dummy_test_installer_plugin.get_installer("othertype")
    assert backend.name == "test_installer"


def test_installer_returns_correct_type(dummy_test_installer_plugin):
    """
    Ensures that our dummy random installer plugin does not get returned for 
    types it is not registered for.
    """
    with pytest.raises(InvalidInstaller):
        dummy_test_installer_plugin.get_installer("idontexist")


def test_raise_error_for_multiple_registered_installers(dummy_test_installer_plugin, dummy_second_test_installer_plugin):
    """
    Ensures that we raise an error when more than one env installer is found
    for the same section.
    """
    with pytest.raises(PluginError):
        dummy_test_installer_plugin.get_installer("test")
