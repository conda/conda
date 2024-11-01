# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause


from conda import plugins

PLUGIN_NAME = "custom_headers"
PLUGIN_NAME_WITH_HOST = "custom_headers_with_host"
HEADER_NAME = "Test-Header"
HEADER_VALUE = "test"


class CustomHeadersPlugin:
    @plugins.hookimpl
    def conda_request_headers(self):
        yield plugins.CondaRequestHeader(
            name=HEADER_NAME, description="test header", value=HEADER_VALUE
        )


class CustomHeadersWithHostPlugin:
    @plugins.hookimpl
    def conda_request_headers(self):
        yield plugins.CondaRequestHeader(
            name=HEADER_NAME,
            description="test",
            value=HEADER_VALUE,
            hosts={"example.com"},
        )


def test_get_auth_handler(plugin_manager):
    """
    Return correct the headers that were defined by the plugin hook
    """
    plugin = CustomHeadersPlugin()
    plugin_manager.register(plugin)

    request_headers = plugin_manager.get_request_headers()

    assert request_headers[0].name == HEADER_NAME
    assert request_headers[0].value == HEADER_VALUE
    assert request_headers[0].hosts is None


def test_get_auth_handler_multiple(plugin_manager):
    """
    Return the correct headers when custom ``hosts`` is defined
    """
    plugin = CustomHeadersWithHostPlugin()
    plugin_manager.register(plugin)

    request_headers = plugin_manager.get_request_headers()

    assert request_headers[0].name == HEADER_NAME
    assert request_headers[0].value == HEADER_VALUE
    assert request_headers[0].hosts == {"example.com"}
