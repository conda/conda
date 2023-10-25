# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import hashlib
import os
from os.path import exists, isfile
from pathlib import Path
from tempfile import mktemp
from unittest.mock import patch

import pytest
import responses
from conda_package_handling.utils import checksum

from conda.base.constants import DEFAULT_CHANNEL_ALIAS
from conda.base.context import conda_tests_ctxt_mgmt_def_pol
from conda.common.io import env_var
from conda.core.subdir_data import SubdirData
from conda.exceptions import (
    CondaDependencyError,
    CondaHTTPError,
    CondaSSLError,
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
)
from conda.models.channel import Channel


@pytest.mark.integration
def test_download_connectionerror():
    with env_var(
        "CONDA_REMOTE_CONNECT_TIMEOUT_SECS",
        1,
        stack_callback=conda_tests_ctxt_mgmt_def_pol,
    ):
        with env_var(
            "CONDA_REMOTE_READ_TIMEOUT_SECS",
            1,
            stack_callback=conda_tests_ctxt_mgmt_def_pol,
        ):
            with env_var(
                "CONDA_REMOTE_MAX_RETRIES",
                1,
                stack_callback=conda_tests_ctxt_mgmt_def_pol,
            ):
                with pytest.raises(CondaHTTPError) as execinfo:
                    url = "http://240.0.0.0/"
                    msg = "Connection error:"
                    download(url, mktemp())
                    assert msg in str(execinfo)


@pytest.mark.integration
def test_fetchrepodate_connectionerror():
    with env_var(
        "CONDA_REMOTE_CONNECT_TIMEOUT_SECS",
        1,
        stack_callback=conda_tests_ctxt_mgmt_def_pol,
    ):
        with env_var(
            "CONDA_REMOTE_READ_TIMEOUT_SECS",
            1,
            stack_callback=conda_tests_ctxt_mgmt_def_pol,
        ):
            with env_var(
                "CONDA_REMOTE_MAX_RETRIES",
                1,
                stack_callback=conda_tests_ctxt_mgmt_def_pol,
            ):
                from conda.base.context import context

                assert context.remote_connect_timeout_secs == 1
                assert context.remote_read_timeout_secs == 1
                assert context.remote_max_retries == 1
                with pytest.raises(CondaHTTPError) as execinfo:
                    url = "http://240.0.0.0/channel/osx-64"
                    msg = "Connection error:"
                    SubdirData(Channel(url)).repo_fetch.fetch_latest()
                    assert msg in str(execinfo)


@pytest.mark.integration
def test_tmpDownload():
    with env_var(
        "CONDA_REMOTE_CONNECT_TIMEOUT_SECS",
        1,
        stack_callback=conda_tests_ctxt_mgmt_def_pol,
    ):
        with env_var(
            "CONDA_REMOTE_READ_TIMEOUT_SECS",
            1,
            stack_callback=conda_tests_ctxt_mgmt_def_pol,
        ):
            with env_var(
                "CONDA_REMOTE_MAX_RETRIES",
                1,
                stack_callback=conda_tests_ctxt_mgmt_def_pol,
            ):
                url = "https://repo.anaconda.com/pkgs/free/osx-64/appscript-1.0.1-py27_0.tar.bz2"
                with TmpDownload(url) as dst:
                    assert exists(dst)
                    assert isfile(dst)

                msg = "Rock and Roll Never Die"
                with TmpDownload(msg) as result:
                    assert result == msg


@responses.activate
def test_resume_download(tmp_path):
    test_file = [b"first:", b"second:", b"last"]
    size = sum(len(line) for line in test_file)
    sha256 = hashlib.new("sha256", data=b"".join(test_file)).hexdigest()

    output_path = tmp_path / "download.tar.bz2"  # double extension
    url = DEFAULT_CHANNEL_ALIAS
    responses.add(
        responses.GET,
        url,
        stream=True,
        content_type="application/octet-stream",
        headers={"Accept-Ranges": "bytes"},
    )

    def iter_content_interrupted(*args, **kwargs):
        yield test_file[0]
        yield test_file[1]
        raise ConnectionAbortedError("Aborted")

    # Download gets interrupted by an exception
    with pytest.raises(ConnectionAbortedError), patch(
        "requests.Response.iter_content", side_effect=iter_content_interrupted
    ):
        download(url, output_path, size=size, sha256=sha256)

    # Check that only the .part file is present
    assert not os.path.exists(output_path)
    assert os.path.exists(str(output_path) + ".partial")

    # Download is resumed
    def iter_content_resumed(*args, **kwargs):
        yield test_file[2]

    # won't resume download unless Partial Content status code
    responses.replace(
        responses.GET,
        url,
        stream=True,
        content_type="application/octet-stream",
        headers={"Accept-Ranges": "bytes"},
        status=206,  # partial content
    )

    with patch("requests.Response.iter_content", side_effect=iter_content_resumed):
        download(url, output_path, size=size, sha256=sha256)

    assert os.path.exists(output_path)
    assert not os.path.exists(str(output_path) + ".partial")

    with open(output_path, "rb") as fh:
        assert fh.read() == b"first:second:last"

    def iter_content_interrupted_2(*args, **kwargs):
        yield test_file[0]
        yield test_file[1]
        response = Response()
        response.status_code = 416
        raise HTTPError(response=response)

    # Download gets interrupted by HTTP 4xx exception; assert `.partial` deleted
    assert not os.path.exists(str(output_path) + ".partial")
    with pytest.raises(CondaHTTPError), patch(
        "requests.Response.iter_content", side_effect=iter_content_interrupted_2
    ):
        download(url, output_path, size=size, sha256=sha256)
    assert not os.path.exists(str(output_path) + ".partial")


@responses.activate
def test_download_when_ranges_not_supported(tmp_path):
    # partial mechanism and `.partial` files sidestepped when size, hash not given
    test_file = [b"first:", b"second:", b"last"]
    size = sum(len(line) for line in test_file)
    sha256 = hashlib.new("sha256", data=b"".join(test_file)).hexdigest()

    output_path = tmp_path / "download.tar.bz2"  # double extension
    partial_path = str(output_path) + ".partial"

    url = DEFAULT_CHANNEL_ALIAS
    responses.add(
        responses.GET,
        url,
        stream=True,
        content_type="application/octet-stream",
        headers={"Accept-Ranges": "none"},
    )

    def iter_content_interrupted(*args, **kwargs):
        yield test_file[0]
        yield test_file[1]
        raise ConnectionAbortedError("aborted")

    with pytest.raises(ConnectionAbortedError), patch(
        "requests.Response.iter_content", side_effect=iter_content_interrupted
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
    partial_path = Path(str(output_path) + ".partial")
    output_path.rename(partial_path)

    with partial_path.open("r+") as partial:
        partial.seek(10)
        partial.truncate()

    # resume from `.partial` file
    download(url, output_path, size=size, sha256=sha256)

    # exercise code that avoids requesting 'range not satisfiable' if partial
    # file is full-size
    partial_path = Path(str(output_path) + ".partial")
    output_path.rename(partial_path)

    download(url, output_path, size=size, sha256=sha256)

    # Get 'range not satisfiable' by requesting a start offset past the end of
    # the file. Imagine we partially download a file, and the remote is replaced
    # by a shorter one before we resume...
    partial_path = Path(str(output_path) + ".partial")
    output_path.rename(partial_path)

    with pytest.raises(CondaHTTPError, match="416"):
        download(url, output_path, size=size * 2, sha256=sha256)

    # Should we special-case deleting this file on 416 to get un-stuck or will a
    # sha256 mismatch save us? (Assuming size, sha256 metadata is eventually
    # consistent with remote file.)
    assert partial_path.exists()

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

    with pytest.raises(ConnectionResetError), download_http_errors(
        "https://example.org/file"
    ):
        raise ConnectionResetError()

    with pytest.raises(ProxyError), download_http_errors("https://example.org/file"):
        raise RequestsProxyError()

    with pytest.raises(CondaDependencyError), download_http_errors(
        "https://example.org/file"
    ):
        raise InvalidSchema("SOCKS")

    with pytest.raises(InvalidSchema), download_http_errors("https://example.org/file"):
        raise InvalidSchema("shoes")  # not a SOCKS problem

    with pytest.raises(CondaSSLError), download_http_errors("https://example.org/file"):
        raise SSLError()

    # A variety of helpful error messages should follow
    with pytest.raises(CondaHTTPError, match=str(401)), download_http_errors(
        "https://example.org/file"
    ):
        raise HTTPError(response=Response(401))
