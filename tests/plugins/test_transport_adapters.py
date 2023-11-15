# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import re

import pytest
import requests
from pytest import CaptureFixture
from requests.models import Response

from conda import plugins
from conda.exceptions import PluginError
from conda.gateways.connection.adapters.http import HTTPAdapter
from conda.gateways.connection.download import download_text
from conda.gateways.connection.session import get_session

PLUGIN_NAME = "http+custom"


class CustomHTTPAdapter(HTTPAdapter):
    def send(self, request, *args, **kwargs):
        print(f"Requesting: {request.url}")
        response = Response()
        response.status_code = requests.codes.ok
        response._content = b"testing"
        response.encoding = "utf-8"
        print(f"Response: {response}")
        return response

    def close(self):
        print("Closing connection: {self}")


class CustomTransportAdapterPlugin:
    @plugins.hookimpl
    def conda_transport_adapters(self):
        yield plugins.CondaTransportAdapter(
            name=PLUGIN_NAME,
            prefix=f"{PLUGIN_NAME}://",
            adapter=CustomHTTPAdapter,
        )


def test_get_transport_adapters(plugin_manager):
    """
    Return the correct transport adapters
    """
    plugin = CustomTransportAdapterPlugin()
    plugin_manager.register(plugin)

    transport_adapters = plugin_manager.get_transport_adapters()
    assert len(transport_adapters) == 1
    assert transport_adapters[PLUGIN_NAME].adapter is CustomHTTPAdapter


def test_duplicated(plugin_manager):
    """
    Make sure that a PluginError is raised if we register the same transport adapter twice.
    """
    plugin_manager.register(CustomTransportAdapterPlugin())
    plugin_manager.register(CustomTransportAdapterPlugin())

    with pytest.raises(
        PluginError, match=re.escape("Conflicting `transport_adapters` plugins found")
    ):
        plugin_manager.get_transport_adapters()


def test_transport_adapter_is_called(plugin_manager, capsys: CaptureFixture):
    """
    Runs the registered transport adapter backend.
    """
    plugin = CustomTransportAdapterPlugin()
    plugin_manager.register(plugin)

    get_session.cache_clear()  # ensuring cleanup
    test_url = f"{PLUGIN_NAME}://example.com/some-file"
    text = download_text(test_url)
    assert text == "testing"

    stdout, stderr = capsys.readouterr()
    assert f"Requesting: {test_url}" in stdout
    assert not stderr
