# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import re

import pytest
from requests.auth import HTTPBasicAuth

from conda import plugins
from conda.exceptions import PluginError

PLUGIN_NAME = "custom_auth"
PLUGIN_NAME_ALT = "custom_auth_alt"


class CustomCondaAuth(HTTPBasicAuth):
    def __init__(self):
        username = "user_one"
        password = "pass_one"
        super().__init__(username, password)


class CustomAltCondaAuth(HTTPBasicAuth):
    def __init__(self):
        username = "user_two"
        password = "pass_two"
        super().__init__(username, password)


class CustomAuthPlugin:
    @plugins.hookimpl
    def conda_auth_handlers(self):
        yield plugins.CondaAuthHandler(handler=CustomCondaAuth, name=PLUGIN_NAME)


class CustomAltAuthPlugin:
    @plugins.hookimpl
    def conda_auth_handlers(self):
        yield plugins.CondaAuthHandler(handler=CustomAltCondaAuth, name=PLUGIN_NAME_ALT)


def test_get_auth_handler(plugin_manager):
    """
    Return the correct auth backend class or return ``None``
    """
    plugin = CustomAuthPlugin()
    plugin_manager.register(plugin)

    auth_handler_cls = plugin_manager.get_auth_handler(PLUGIN_NAME)
    assert auth_handler_cls is CustomCondaAuth

    auth_handler_cls = plugin_manager.get_auth_handler("DOES_NOT_EXIST")
    assert auth_handler_cls is None


def test_get_auth_handler_multiple(plugin_manager):
    """
    Tests to make sure we can retrieve auth backends when there are multiple hooks registered.
    """
    plugin_one = CustomAuthPlugin()
    plugin_two = CustomAltAuthPlugin()
    plugin_manager.register(plugin_one)
    plugin_manager.register(plugin_two)

    auth_class = plugin_manager.get_auth_handler(PLUGIN_NAME)
    assert auth_class is CustomCondaAuth

    auth_class = plugin_manager.get_auth_handler(PLUGIN_NAME_ALT)
    assert auth_class is CustomAltCondaAuth


def test_duplicated(plugin_manager):
    """
    Make sure that a PluginError is raised if we register the same auth backend twice.
    """
    plugin_manager.register(CustomAuthPlugin())
    plugin_manager.register(CustomAuthPlugin())

    with pytest.raises(
        PluginError, match=re.escape("Conflicting `auth_handlers` plugins found")
    ):
        plugin_manager.get_auth_handler(PLUGIN_NAME)
