# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import re

import pytest

from conda.exceptions import PluginError
from conda.gateways.connection.session import CondaSession
from conda.plugins.hookspec import hookimpl
from conda.plugins.types import CondaFetch

PLUGIN_NAME = "custom_session"
PLUGIN_NAME_ALT = "custom_session_alt"


class CustomCondaSession(CondaSession):
    def __init__(self):
        self.custom = PLUGIN_NAME

        super().__init__()


class CustomAltCondaSession(CondaSession):
    def __init__(self):
        self.custom = PLUGIN_NAME_ALT

        super().__init__()


class CustomFetchPlugin:
    @hookimpl
    def conda_fetch(self):
        yield CondaFetch(session_class=CustomCondaSession, name=PLUGIN_NAME)


class CustomAltFetchPlugin:
    @hookimpl
    def conda_fetch(self):
        yield CondaFetch(session_class=CustomAltCondaSession, name=PLUGIN_NAME_ALT)


def test_get_fetch_backend(plugin_manager):
    """
    When the ``get_fetch_backend`` method is called without arguments, it should
    return the default ``CondaSession`` class, otherwise it will return any classes
    that are part of the registered fetch plugins.

    If a plugin is not found, return the default ``CondaSession`` class too.
    """
    plugin = CustomFetchPlugin()
    plugin_manager.register(plugin)

    session_class = plugin_manager.get_fetch_backend()
    assert session_class is CondaSession

    session_class = plugin_manager.get_fetch_backend(PLUGIN_NAME)
    assert session_class is CustomCondaSession

    session_class = plugin_manager.get_fetch_backend("DOES_NOT_EXIST")
    assert session_class is CondaSession


def test_get_fetch_backend_multiple(plugin_manager):
    """
    Tests to make sure we can retrieve fetch backends when there are multiple hooks registered.
    """
    plugin_one = CustomFetchPlugin()
    plugin_two = CustomAltFetchPlugin()
    plugin_manager.register(plugin_one)
    plugin_manager.register(plugin_two)

    session_class = plugin_manager.get_fetch_backend(PLUGIN_NAME)
    assert session_class is CustomCondaSession

    session_class = plugin_manager.get_fetch_backend(PLUGIN_NAME_ALT)
    assert session_class is CustomAltCondaSession


def test_duplicated(plugin_manager):
    """
    Make sure that a PluginError is raised if we register the same fetch backend twice.
    """
    plugin_manager.register(CustomFetchPlugin())
    plugin_manager.register(CustomFetchPlugin())

    with pytest.raises(
        PluginError, match=re.escape("Conflicting `fetch` plugins found")
    ):
        plugin_manager.get_fetch_backend(PLUGIN_NAME)
