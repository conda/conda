# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from os.path import exists, isfile
from tempfile import mktemp

import pytest
import responses

from conda.base.constants import DEFAULT_CHANNEL_ALIAS
from conda.base.context import conda_tests_ctxt_mgmt_def_pol
from conda.common.io import env_var
from conda.core.package_cache_data import download
from conda.core.subdir_data import SubdirData
from conda.exceptions import CondaHTTPError
from conda.gateways.connection.download import TmpDownload
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
