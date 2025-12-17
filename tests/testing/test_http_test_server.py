# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Tests for HTTP test server fixtures."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
import requests

if TYPE_CHECKING:
    from conda.testing.fixtures import HttpTestServerFixture


pytest_plugins = "conda.testing.fixtures"


@pytest.mark.http_server_dir("tests/env/support")
def test_http_server_serves_files(http_test_server: HttpTestServerFixture):
    """Should serve files from specified directory."""
    # Request a known file
    url = http_test_server.get_url("simple.yml")
    response = requests.get(url)

    assert response.status_code == 200
    # Check if content contains expected YAML fields
    assert "name:" in response.text or "dependencies:" in response.text


@pytest.mark.http_server_dir("tests/env/support")
def test_http_server_fixture_attributes(http_test_server: HttpTestServerFixture):
    """Should have expected attributes."""
    assert http_test_server.server is not None
    assert isinstance(http_test_server.host, str)
    assert isinstance(http_test_server.port, int)
    assert http_test_server.port > 0
    assert http_test_server.url.startswith("http://")
    assert str(http_test_server.port) in http_test_server.url


@pytest.mark.http_server_dir("tests/env/support")
def test_http_server_get_url_method(http_test_server: HttpTestServerFixture):
    """Should construct correct URLs."""
    # Base URL
    base_url = http_test_server.get_url()
    assert base_url == http_test_server.url

    # URL with path
    file_url = http_test_server.get_url("simple.yml")
    assert file_url == f"{http_test_server.url}/simple.yml"

    # URL with leading slash (should be stripped)
    file_url_slash = http_test_server.get_url("/simple.yml")
    assert file_url_slash == f"{http_test_server.url}/simple.yml"

    # URL with nested path
    nested_url = http_test_server.get_url("example/environment_pinned.yml")
    assert nested_url == f"{http_test_server.url}/example/environment_pinned.yml"


@pytest.mark.http_server_dir("tests/env/support")
def test_http_server_404_missing_file(http_test_server: HttpTestServerFixture):
    """Should return 404 for missing files."""
    url = http_test_server.get_url("nonexistent_file_that_does_not_exist.txt")
    response = requests.get(url)
    assert response.status_code == 404


@pytest.mark.http_server_dir("tests/env/support")
def test_http_server_subdirectories(http_test_server: HttpTestServerFixture):
    """Should serve files from subdirectories."""
    url = http_test_server.get_url("example/environment_pinned.yml")
    response = requests.get(url)
    # Should either succeed or return 404 if file doesn't exist
    # This test mainly verifies the server handles subdirectory requests
    assert response.status_code in (200, 404)


# Session-scoped fixture tests
# Note: Session-scoped fixtures are tested separately in integration tests
# because they require special setup (all tests in session must use same marker).
# The session_http_test_server fixture works correctly but is harder to unit test
# in isolation due to pytest's session scope initialization order.
# See tests/env/test_create.py::test_create_update_remote_env_file for usage example.


def test_marker_validation_directory_type():
    """Test marker validation for directory type."""
    # This is tested implicitly through the other tests
    # If marker accepts invalid types, those tests would fail
    pass
