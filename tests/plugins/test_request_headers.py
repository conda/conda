# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from conda.plugins import CondaRequestHeader, hookimpl

if TYPE_CHECKING:
    from collections.abc import Iterator

    from conda.common.url import Url

STATIC_HEADER = CondaRequestHeader(name="Static-Header", value="static-value")
HOST_HEADER = CondaRequestHeader(name="Host-Header", value="host-value")
ENDPOINT_HEADER = CondaRequestHeader(name="Endpoint-Header", value="endpoint-value")

EXAMPLE_HOST = "example.com"
EXAMPLE_BASE_URL = f"https://{EXAMPLE_HOST}"
EXAMPLE_ENDPOINT = "endpoint.json"


class CustomHeadersPlugin:
    @hookimpl
    def conda_request_headers(
        self, method: str, url: Url
    ) -> Iterator[CondaRequestHeader]:
        # always include header
        yield STATIC_HEADER

        # only include header for specific domain/host/netloc
        if url.scheme in ("https", "http") and url.netloc in {EXAMPLE_HOST}:
            yield HOST_HEADER

            # only include header for specific path/endpoint
            if url.path.endswith(f"/{EXAMPLE_ENDPOINT}"):
                yield ENDPOINT_HEADER


@pytest.mark.parametrize(
    "url,dynamic_host,dynamic_endpoint",
    [
        pytest.param(url := "random.com", False, False, id=f"static header ({url})"),
        pytest.param(
            url := "https://random.com", False, False, id=f"static header ({url})"
        ),
        pytest.param(url := EXAMPLE_HOST, False, False, id=f"static header ({url})"),
        pytest.param(url := EXAMPLE_BASE_URL, True, False, id=f"host header ({url})"),
        pytest.param(
            url := f"{EXAMPLE_BASE_URL}/path/somewhere.txt",
            True,
            False,
            id=f"host header ({url})",
        ),
        pytest.param(
            url := f"{EXAMPLE_BASE_URL}/path/{EXAMPLE_ENDPOINT}",
            True,
            True,
            id=f"endpoint header ({url})",
        ),
    ],
)
def test_get_auth_handler(
    plugin_manager,
    url: str,
    dynamic_host: bool,
    dynamic_endpoint: bool,
) -> None:
    """
    Return correct the headers that were defined by the plugin hook
    """
    plugin = CustomHeadersPlugin()
    plugin_manager.register(plugin)

    request_headers = plugin_manager.get_request_headers("GET", url)
    assert len(request_headers) == (1 + dynamic_host + dynamic_endpoint)

    assert request_headers[STATIC_HEADER.name] == STATIC_HEADER.value

    if dynamic_host:
        assert request_headers[HOST_HEADER.name] == HOST_HEADER.value

    if dynamic_endpoint:
        assert request_headers[ENDPOINT_HEADER.name] == ENDPOINT_HEADER.value
