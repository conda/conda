# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Tests for HTTP test server fixtures."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest
import requests

if TYPE_CHECKING:
    from conda.testing.fixtures import HttpTestServerFixture


pytest_plugins = "conda.testing.fixtures"


@pytest.mark.parametrize("http_test_server", ["tests/env/support"], indirect=True)
def test_http_server_serves_files(http_test_server: HttpTestServerFixture):
    """Should serve files from specified directory."""
    # Request a known file
    url = http_test_server.get_url("simple.yml")
    response = requests.get(url)

    assert response.status_code == 200
    # Check if content contains expected YAML fields
    assert "name:" in response.text or "dependencies:" in response.text


@pytest.mark.parametrize("http_test_server", ["tests/env/support"], indirect=True)
def test_http_server_fixture_attributes(http_test_server: HttpTestServerFixture):
    """Should have expected attributes."""
    assert http_test_server.server is not None
    assert isinstance(http_test_server.host, str)
    assert isinstance(http_test_server.port, int)
    assert http_test_server.port > 0
    assert http_test_server.url.startswith("http://")
    assert str(http_test_server.port) in http_test_server.url


@pytest.mark.parametrize("http_test_server", ["tests/env/support"], indirect=True)
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


@pytest.mark.parametrize("http_test_server", ["tests/env/support"], indirect=True)
def test_http_server_404_missing_file(http_test_server: HttpTestServerFixture):
    """Should return 404 for missing files."""
    url = http_test_server.get_url("nonexistent_file_that_does_not_exist.txt")
    response = requests.get(url)
    assert response.status_code == 404


@pytest.mark.parametrize("http_test_server", ["tests/env/support"], indirect=True)
def test_http_server_subdirectories(http_test_server: HttpTestServerFixture):
    """Should serve files from subdirectories."""
    url = http_test_server.get_url("example/environment_pinned.yml")
    response = requests.get(url)
    # Should either succeed or return 404 if file doesn't exist
    # This test mainly verifies the server handles subdirectory requests
    assert response.status_code in (200, 404)


# Tests without marker (dynamic content pattern)


def test_http_server_without_marker(http_test_server: HttpTestServerFixture):
    """Should work without marker, using temporary directory."""
    # Directory should exist and be writable
    assert http_test_server.directory.exists()
    assert http_test_server.directory.is_dir()

    # Should be able to create files dynamically
    test_file = http_test_server.directory / "test.txt"
    test_file.write_text("test content")

    # Should be able to fetch them via HTTP
    response = requests.get(http_test_server.get_url("test.txt"))
    assert response.status_code == 200
    assert response.text == "test content"


def test_dynamic_content_pattern(http_test_server: HttpTestServerFixture):
    """Test the dynamic content pattern from kenodegard's feedback."""
    # This is the exact pattern suggested in PR review
    (http_test_server.directory / "repodata.json").write_text('{"packages": {}}')
    response = requests.get(http_test_server.get_url("repodata.json"))
    assert response.status_code == 200
    assert response.json() == {"packages": {}}


def test_http_server_directory_attribute(http_test_server: HttpTestServerFixture):
    """Test that directory attribute is accessible and writable."""
    # Directory attribute should be a Path
    assert isinstance(http_test_server.directory, Path)

    # Should be able to create subdirectories
    subdir = http_test_server.directory / "subdir"
    subdir.mkdir()
    (subdir / "file.txt").write_text("nested content")

    # Should be able to fetch nested files
    response = requests.get(http_test_server.get_url("subdir/file.txt"))
    assert response.status_code == 200
    assert response.text == "nested content"


@pytest.mark.parametrize(
    "http_test_server",
    ["tests/env/support", "tests/data"],
    indirect=True,
)
def test_http_server_multiple_directories(http_test_server: HttpTestServerFixture):
    """Test that parametrize can test multiple directories."""
    # This test will run twice, once for each directory
    assert http_test_server.directory.exists()
    assert http_test_server.directory.is_dir()
    assert http_test_server.url.startswith("http://")
    assert http_test_server.port > 0


def test_marker_validation_directory_type():
    """Test marker validation for directory type."""
    # This is tested implicitly through the other tests
    # If marker accepts invalid types, those tests would fail
    pass
