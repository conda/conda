# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import hashlib
import os
import re
from contextlib import nullcontext
from os.path import exists, isfile
from pathlib import Path
from tempfile import mktemp
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
import responses.matchers
import responses.registries
from conda_package_handling.utils import checksum

from conda.base.constants import DEFAULT_CHANNEL_ALIAS, PARTIAL_EXTENSION
from conda.base.context import context, reset_context
from conda.core.subdir_data import SubdirData
from conda.exceptions import (
    CondaDependencyError,
    CondaHTTPError,
    CondaSSLError,
    CondaValueError,
    ProxyError,
)
from conda.gateways.connection import (
    HTTPError,
    InvalidSchema,
    RequestsProxyError,
    Response,
    SSLError,
)
from conda.gateways.connection.download import (
    TmpDownload,
    download,
    download_http_errors,
    download_text,
)
from conda.models.channel import Channel

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any

    from pytest import MonkeyPatch

pytestmark = pytest.mark.usefixtures("clear_conda_session_cache")


@pytest.mark.integration
def test_download_connectionerror(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("CONDA_REMOTE_CONNECT_TIMEOUT_SECS", "1")
    monkeypatch.setenv("CONDA_REMOTE_READ_TIMEOUT_SECS", "1")
    monkeypatch.setenv("CONDA_REMOTE_MAX_RETRIES", "1")
    reset_context()
    assert context.remote_connect_timeout_secs == 1
    assert context.remote_read_timeout_secs == 1
    assert context.remote_max_retries == 1

    with pytest.raises(CondaHTTPError, match=r"CONNECTION FAILED for url"):
        url = "http://240.0.0.0/"
        download(url, tmp_path)


@pytest.mark.integration
def test_fetchrepodate_connectionerror(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("CONDA_REMOTE_CONNECT_TIMEOUT_SECS", "1")
    monkeypatch.setenv("CONDA_REMOTE_READ_TIMEOUT_SECS", "1")
    monkeypatch.setenv("CONDA_REMOTE_MAX_RETRIES", "1")
    reset_context()
    assert context.remote_connect_timeout_secs == 1
    assert context.remote_read_timeout_secs == 1
    assert context.remote_max_retries == 1

    with pytest.raises(CondaHTTPError, match=r"CONNECTION FAILED for url"):
        url = "http://240.0.0.0/channel/osx-64"
        SubdirData(Channel(url)).repo_fetch.fetch_latest()


@pytest.mark.integration
def test_tmpDownload(monkeypatch: MonkeyPatch):
    monkeypatch.setenv("CONDA_REMOTE_CONNECT_TIMEOUT_SECS", "1")
    monkeypatch.setenv("CONDA_REMOTE_READ_TIMEOUT_SECS", "1")
    monkeypatch.setenv("CONDA_REMOTE_MAX_RETRIES", "1")
    reset_context()
    assert context.remote_connect_timeout_secs == 1
    assert context.remote_read_timeout_secs == 1
    assert context.remote_max_retries == 1

    url = "https://repo.anaconda.com/pkgs/free/osx-64/appscript-1.0.1-py27_0.tar.bz2"
    with TmpDownload(url) as dst:
        assert exists(dst)
        assert isfile(dst)

    msg = "Rock and Roll Never Die"
    with TmpDownload(msg) as result:
        assert result == msg


@responses.activate
def test_resume_download(tmp_path):
    # This test works offline.
    test_file = [b"first:", b"second:", b"last"]
    size = len(b"".join(test_file))
    sha256 = hashlib.new("sha256", data=b"".join(test_file)).hexdigest()

    output_path = tmp_path / "download.tar.bz2"  # double extension
    url = DEFAULT_CHANNEL_ALIAS
    # allow the test to pass if we are using /t/<token> auth:
    url_pattern = re.compile(f"{url}.*")
    responses.add(
        responses.GET,
        url_pattern,
        content_type="application/octet-stream",
        headers={"Accept-Ranges": "bytes"},
    )

    def iter_content_interrupted(*args, **kwargs):
        yield test_file[0]
        yield test_file[1]
        raise ConnectionAbortedError("Aborted")

    # Download gets interrupted by an exception
    with (
        pytest.raises(ConnectionAbortedError),
        patch("requests.Response.iter_content", side_effect=iter_content_interrupted),
    ):
        download(url, output_path, size=size, sha256=sha256)

    # Check that only the partial file is present
    assert not os.path.exists(output_path)
    assert os.path.exists(str(output_path) + PARTIAL_EXTENSION)

    # Download is resumed
    def iter_content_resumed(*args, **kwargs):
        yield test_file[2]

    # won't resume download unless Partial Content status code
    responses.replace(
        responses.GET,
        url_pattern,
        content_type="application/octet-stream",
        headers={"Accept-Ranges": "bytes"},
        status=206,  # partial content
    )

    with patch("requests.Response.iter_content", side_effect=iter_content_resumed):
        download(url, output_path, size=size, sha256=sha256)

    assert os.path.exists(output_path)
    assert not os.path.exists(str(output_path) + PARTIAL_EXTENSION)

    with open(output_path, "rb") as fh:
        assert fh.read() == b"first:second:last"

    def iter_content_interrupted_2(*args, **kwargs):
        yield test_file[0]
        yield test_file[1]
        response = Response()
        response.status_code = 416
        raise HTTPError(response=response)

    # Download gets interrupted by HTTP 4xx exception; assert partial file deleted
    assert not os.path.exists(str(output_path) + PARTIAL_EXTENSION)
    with (
        pytest.raises(CondaHTTPError),
        patch("requests.Response.iter_content", side_effect=iter_content_interrupted_2),
    ):
        download(url, output_path, size=size, sha256=sha256)
    assert not os.path.exists(str(output_path) + PARTIAL_EXTENSION)


@responses.activate
def test_download_when_ranges_not_supported(tmp_path):
    # partial mechanism and partial files sidestepped when size, hash not given
    # This test works offline.
    test_file = [b"first:", b"second:", b"last"]
    size = sum(len(line) for line in test_file)
    sha256 = hashlib.new("sha256", data=b"".join(test_file)).hexdigest()

    output_path = tmp_path / "download.tar.bz2"  # double extension
    partial_path = str(output_path) + PARTIAL_EXTENSION

    url = DEFAULT_CHANNEL_ALIAS
    # allow the test to pass if we are using /t/<token> auth:
    url_pattern = re.compile(f"{url}.*")
    responses.add(
        responses.GET,
        url_pattern,
        content_type="application/octet-stream",
        headers={"Accept-Ranges": "none"},
    )

    def iter_content_interrupted(*args, **kwargs):
        yield test_file[0]
        yield test_file[1]
        raise ConnectionAbortedError("aborted")

    with (
        pytest.raises(ConnectionAbortedError),
        patch("requests.Response.iter_content", side_effect=iter_content_interrupted),
    ):
        download(url, output_path, size=size, sha256=sha256)

    assert not os.path.exists(output_path)
    assert os.path.exists(partial_path)

    # Accept-Ranges is not supported, send full content
    with patch("requests.Response.iter_content") as iter_content_mock:

        def iter_content_resumed(*args, **kwargs):
            yield b"".join(test_file)

        iter_content_mock.side_effect = iter_content_resumed
        download(url, output_path, size=size, sha256=sha256)

    assert os.path.exists(output_path)
    assert not os.path.exists(partial_path)

    with open(output_path, "rb") as fh:
        assert fh.read() == b"".join(test_file)


@responses.activate
def test_download_httperror():
    with pytest.raises(CondaHTTPError) as execinfo:
        url = DEFAULT_CHANNEL_ALIAS
        msg = "HTTPError:"
        responses.add(
            responses.GET,
            url,
            body='{"error": "not found"}',
            status=404,
            content_type="application/json",
        )
        download(url, mktemp())
        assert msg in str(execinfo)


def test_resume_partial(tmp_path: Path, package_repository_base, package_server):
    host, port = package_server.getsockname()
    base = f"http://{host}:{port}/test"
    package_name = "zlib-1.2.11-h7b6447c_3.conda"
    url = f"{base}/linux-64/{package_name}"
    package_path = package_repository_base / "linux-64" / package_name
    sha256 = checksum(package_path, algorithm="sha256")
    size = package_path.stat().st_size
    output_path = tmp_path / package_name

    called = False

    def progress_update_callback(amount):
        nonlocal called
        called = True

    # try full download
    download(
        url,
        output_path,
        size=size,
        sha256=sha256,
        progress_update_callback=progress_update_callback,
    )

    assert called

    # simulate partial download
    partial_path = Path(str(output_path) + PARTIAL_EXTENSION)
    output_path.rename(partial_path)

    with partial_path.open("r+") as partial:
        partial.seek(10)
        partial.truncate()

    # resume from partial file
    download(url, output_path, size=size, sha256=sha256)

    # exercise code that avoids requesting 'range not satisfiable' if partial
    # file is full-size
    partial_path = Path(str(output_path) + PARTIAL_EXTENSION)
    output_path.rename(partial_path)

    download(url, output_path, size=size, sha256=sha256)

    # Get 'range not satisfiable' by requesting a start offset past the end of
    # the file. Imagine we partially download a file, and the remote is replaced
    # by a shorter one before we resume...
    partial_path = Path(str(output_path) + PARTIAL_EXTENSION)
    output_path.rename(partial_path)

    with pytest.raises(CondaHTTPError, match="416"):
        download(url, output_path, size=size * 2, sha256=sha256)

    # Special-cased deleting this file on 4xx errors
    assert not partial_path.exists()

    with pytest.raises(Exception, match="mismatch"):
        download(url, output_path, size=size // 2, sha256=sha256)

    # We may or may not want to preserve this behavior, but it is what the
    # download() function has done in the past.
    assert not output_path.exists()
    # output_path.unlink()

    download(url, output_path, size=size, sha256=sha256)


def test_download_http_errors():
    class Response:
        def __init__(self, status_code):
            self.status_code = status_code

    with (
        pytest.raises(ConnectionResetError),
        download_http_errors("https://example.org/file"),
    ):
        raise ConnectionResetError()

    with pytest.raises(ProxyError), download_http_errors("https://example.org/file"):
        raise RequestsProxyError()

    with (
        pytest.raises(CondaDependencyError),
        download_http_errors("https://example.org/file"),
    ):
        raise InvalidSchema("SOCKS")

    with pytest.raises(InvalidSchema), download_http_errors("https://example.org/file"):
        raise InvalidSchema("shoes")  # not a SOCKS problem

    with pytest.raises(CondaSSLError), download_http_errors("https://example.org/file"):
        raise SSLError()

    # A variety of helpful error messages should follow

    # 401 on generic URL
    with (
        pytest.raises(CondaHTTPError, match="credentials you have provided"),
        download_http_errors("https://example.org/file"),
    ):
        raise HTTPError(response=Response(401))

    # 401 with token should trigger token-specific message
    with (
        pytest.raises(CondaHTTPError, match="token.*is invalid"),
        download_http_errors(
            "/t/dh-73683400-b3ee-4f87-ade8-37de6d395bdb/conda-forge/file"
        ),
    ):
        raise HTTPError(response=Response(401))

    # 403 on generic URL
    with (
        pytest.raises(CondaHTTPError, match="do not have permission"),
        download_http_errors("https://example.org/file"),
    ):
        raise HTTPError(response=Response(403))

    # 403 with token should trigger token-specific message
    with (
        pytest.raises(CondaHTTPError, match="insufficient permissions"),
        download_http_errors(
            "/t/dh-73683400-b3ee-4f87-ade8-37de6d395bdb/conda-forge/file"
        ),
    ):
        raise HTTPError(response=Response(403))

    # Other HTTP errors should use generic message
    with (
        pytest.raises(CondaHTTPError, match="An HTTP error"),
        download_http_errors("https://example.org/file"),
    ):
        raise HTTPError(response=Response(500))


@pytest.mark.parametrize(
    "raises,get_sha256",
    [
        pytest.param(False, lambda x: x, id="original"),
        pytest.param(False, str.upper, id="upper"),
        pytest.param(True, lambda x: "not-an-hex-string", id="gibberish"),
        pytest.param(True, lambda x: 123456, id="bad-type"),
    ],
)
def test_checksum_checks_bytes(
    tmp_path: Path,
    package_repository_base,
    package_server,
    raises: bool,
    get_sha256: Callable[[str], Any],
):
    host, port = package_server.getsockname()
    base = f"http://{host}:{port}/test"
    package_name = "zlib-1.2.11-h7b6447c_3.conda"
    url = f"{base}/linux-64/{package_name}"
    package_path = package_repository_base / "linux-64" / package_name
    sha256 = checksum(package_path, algorithm="sha256")
    size = package_path.stat().st_size
    output_path = tmp_path / package_name

    with pytest.raises(CondaValueError) if raises else nullcontext():
        download(url, output_path, size=size, sha256=get_sha256(sha256))


@responses.activate
def test_download_text():
    test_file = b"text"

    url = DEFAULT_CHANNEL_ALIAS
    # allow the test to pass if we are using /t/<token> auth:
    url_pattern = re.compile(f"{url}.*")
    responses.add(
        responses.GET,
        url_pattern,
        content_type="application/octet-stream",
        body=test_file,
    )

    assert download_text(DEFAULT_CHANNEL_ALIAS) == test_file.decode("ascii")


@responses.activate(registry=responses.registries.OrderedRegistry)
def test_resume_bad_partial(tmp_path: Path):
    """
    Test retry when partial file is corrupted.
    """
    test_file = b"data"
    size = len(test_file)
    sha256 = hashlib.sha256(test_file).hexdigest()
    output_path = tmp_path / "test_file"

    url = "http://example.org/test_file"

    # won't resume download unless Partial Content status code
    responses.add(
        responses.GET,
        url,
        content_type="application/octet-stream",
        headers={"Accept-Ranges": "bytes"},
        status=206,  # partial content
        body=test_file[1:],
        match=[
            responses.matchers.header_matcher({"Range": "bytes=1-"}),
        ],
    )

    responses.add(
        responses.GET,
        url,
        content_type="application/octet-stream",
        headers={"Accept-Ranges": "bytes"},
        status=200,
        body=test_file,
    )

    # simulate partial download
    partial_path = Path(str(output_path) + PARTIAL_EXTENSION)
    partial_path.write_text("x")

    # resume from partial file
    download(url, output_path, size=size, sha256=sha256)

    assert output_path.read_bytes() == test_file


@responses.activate
def test_download_size_none(tmp_path: Path):
    """
    Test download with no size.
    """
    test_file = b"data"
    sha256 = hashlib.sha256(test_file).hexdigest()
    output_path = tmp_path / "test_file"

    url = "http://example.org/test_file"

    responses.add(
        responses.GET,
        url,
        content_type="application/octet-stream",
        headers={"Accept-Ranges": "bytes"},
        status=200,
        body=test_file,
    )

    # no size given
    download(url, output_path, sha256=sha256)

    assert output_path.read_bytes() == test_file
