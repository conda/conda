# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import hashlib
import os
from os.path import exists, isfile
from tempfile import mktemp
from unittest.mock import patch

import pytest
import responses

from conda.base.constants import DEFAULT_CHANNEL_ALIAS
from conda.base.context import conda_tests_ctxt_mgmt_def_pol
from conda.common.io import env_var
from conda.core.subdir_data import SubdirData
from conda.exceptions import CondaHTTPError
from conda.gateways.connection.download import TmpDownload, download
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
def test_resume_download():
    test_file = [b"first:", b"second:", b"last"]
    size = sum(len(line) for line in test_file)
    sha256 = hashlib.new("sha256", data=b"".join(test_file)).hexdigest()

    output_path = mktemp()
    url = DEFAULT_CHANNEL_ALIAS
    responses.add(
        responses.GET,
        url,
        stream=True,
        content_type="application/octet-stream",
        headers={"Accept-Ranges": "bytes"},
    )
    # Download gets interrupted by an exception
    with pytest.raises(ConnectionAbortedError):

        def iter_content_interrupted(*args, **kwargs):
            yield test_file[0]
            yield test_file[1]
            raise ConnectionAbortedError("aborted")

        with patch(
            "requests.Response.iter_content", side_effect=iter_content_interrupted
        ):
            download(url, output_path, size=size, sha256=sha256)

    # Check that only the .part file is present
    assert not os.path.exists(output_path)
    assert os.path.exists(output_path + ".partial")

    # Download is resumed
    def iter_content_resumed(*args, **kwargs):
        yield test_file[2]

    # won't resume download unless 216 Partial Content status code
    responses.replace(
        responses.GET,
        url,
        stream=True,
        content_type="application/octet-stream",
        headers={"Accept-Ranges": "bytes"},
        status=216,
    )

    with patch("requests.Response.iter_content", side_effect=iter_content_resumed):
        download(url, output_path, size=size, sha256=sha256)

    assert os.path.exists(output_path)
    assert not os.path.exists(output_path + ".partial")

    with open(output_path, "rb") as fh:
        assert fh.read() == b"first:second:last"


@responses.activate
def test_download_when_ranges_not_supported():
    output_path = mktemp()
    with pytest.raises(ConnectionAbortedError):
        url = DEFAULT_CHANNEL_ALIAS
        responses.add(
            responses.GET,
            url,
            stream=True,
            content_type="application/json",
            headers={"Accept-Ranges": "none"},
        )
        with patch("requests.Response.iter_content") as iter_content_mock:

            def iter_content_interrupted(*args, **kwargs):
                yield b"first:"
                yield b"second:"
                raise ConnectionAbortedError("aborted")

            iter_content_mock.side_effect = iter_content_interrupted
            download(url, output_path)

    assert not os.path.exists(output_path)
    assert os.path.exists(output_path + ".partial")

    # Accept-Ranges is not supported, send full content
    with patch("requests.Response.iter_content") as iter_content_mock:

        def iter_content_resumed(*args, **kwargs):
            yield b"first:second:last"

        iter_content_mock.side_effect = iter_content_resumed
        download(url, output_path)

    assert os.path.exists(output_path)
    assert not os.path.exists(output_path + ".partial")

    with open(output_path, "rb") as fh:
        assert fh.read() == b"first:second:last"


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
