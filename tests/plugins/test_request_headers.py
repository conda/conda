# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from conda.common.url import urlparse
from conda.plugins import hookimpl
from conda.plugins.types import CondaRequestHeader

if TYPE_CHECKING:
    from collections.abc import Iterator

    from conda.common.url import Url

STATIC_HEADER = CondaRequestHeader(name="Static-Header", value="static-value")
HOST_HEADER = CondaRequestHeader(name="Host-Header", value="host-value")
ENDPOINT_HEADER = CondaRequestHeader(name="Endpoint-Header", value="endpoint-value")
NOT_ENDPOINT_HEADER = CondaRequestHeader(
    name="Not-Endpoint-Header", value="not-endpoint-value"
)

EXAMPLE_HOST = "example.com"
EXAMPLE_ENDPOINT = "/endpoint.json"


class CustomHeadersPlugin:
    @hookimpl
    def conda_session_headers(self, host: str) -> Iterator[CondaRequestHeader]:
        # always include header
        yield STATIC_HEADER

        # only include header for specific domain/host/netloc
        if host in {EXAMPLE_HOST}:
            yield HOST_HEADER

    @hookimpl
    def conda_request_headers(self, path: str) -> Iterator[CondaRequestHeader]:
        # only include header for specific path/endpoint
        if path == EXAMPLE_ENDPOINT:
            yield ENDPOINT_HEADER
        else:
            yield NOT_ENDPOINT_HEADER


@pytest.mark.parametrize(
    "url,host_header",
    [
        pytest.param(url := "random.com", False, id=url),
        pytest.param(url := EXAMPLE_HOST, True, id=url),
        pytest.param(url := f"{EXAMPLE_HOST}/path/somewhere.txt", True, id=url),
        pytest.param(url := f"{EXAMPLE_HOST}{EXAMPLE_ENDPOINT}", True, id=url),
        pytest.param(url := f"random.com{EXAMPLE_ENDPOINT}", False, id=url),
    ],
)
def test_get_session_headers(plugin_manager, url: str | Url, host_header: bool) -> None:
    """
    Return the session headers that were defined by the plugin hook
    """
    plugin_manager.register(CustomHeadersPlugin())

    url = urlparse(url)
    request_headers = plugin_manager.get_session_headers(host=url.netloc)
    assert len(request_headers) == (1 + host_header)

    assert request_headers[STATIC_HEADER.name] == STATIC_HEADER.value
    if host_header:
        assert request_headers[HOST_HEADER.name] == HOST_HEADER.value


@pytest.mark.parametrize(
    "url,endpoint_header",
    [
        pytest.param(url := "random.com", False, id=url),
        pytest.param(url := EXAMPLE_HOST, False, id=url),
        pytest.param(url := f"{EXAMPLE_HOST}/path/somewhere.txt", False, id=url),
        pytest.param(url := f"{EXAMPLE_HOST}{EXAMPLE_ENDPOINT}", True, id=url),
        pytest.param(url := f"random.com{EXAMPLE_ENDPOINT}", True, id=url),
    ],
)
def test_get_request_headers(
    plugin_manager, url: str | Url, endpoint_header: bool
) -> None:
    """
    Return the request headers that were defined by the plugin hook
    """
    plugin_manager.register(CustomHeadersPlugin())

    url = urlparse(url)
    request_headers = plugin_manager.get_request_headers(host=url.netloc, path=url.path)
    assert len(request_headers) == 1

    if endpoint_header:
        assert request_headers[ENDPOINT_HEADER.name] == ENDPOINT_HEADER.value
    else:
        assert request_headers[NOT_ENDPOINT_HEADER.name] == NOT_ENDPOINT_HEADER.value
