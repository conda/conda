# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

import os
from unittest import TestCase

import pytest
import responses
from os.path import exists, isfile
from tempfile import mktemp

from conda.base.constants import DEFAULT_CHANNEL_ALIAS
from conda.base.context import conda_tests_ctxt_mgmt_def_pol
from conda.common.io import env_var
from conda.exceptions import CondaHTTPError
from conda.gateways.connection.download import TmpDownload
from conda.core.subdir_data import fetch_repodata_remote_request
from conda.core.package_cache_data import download


@pytest.mark.integration
class TestConnectionWithShortTimeouts(TestCase):

    def test_download_connectionerror(self):
        with env_var('CONDA_REMOTE_CONNECT_TIMEOUT_SECS', 1, stack_callback=conda_tests_ctxt_mgmt_def_pol):
            with env_var('CONDA_REMOTE_READ_TIMEOUT_SECS', 1, stack_callback=conda_tests_ctxt_mgmt_def_pol):
                with env_var('CONDA_REMOTE_MAX_RETRIES', 1, stack_callback=conda_tests_ctxt_mgmt_def_pol):
                    with pytest.raises(CondaHTTPError) as execinfo:
                        url = "http://240.0.0.0/"
                        msg = "Connection error:"
                        download(url, mktemp())
                        assert msg in str(execinfo)

    def test_fetchrepodate_connectionerror(self):
        with env_var('CONDA_REMOTE_CONNECT_TIMEOUT_SECS', 1, stack_callback=conda_tests_ctxt_mgmt_def_pol):
            with env_var('CONDA_REMOTE_READ_TIMEOUT_SECS', 1, stack_callback=conda_tests_ctxt_mgmt_def_pol):
                with env_var('CONDA_REMOTE_MAX_RETRIES', 1, stack_callback=conda_tests_ctxt_mgmt_def_pol):
                    with pytest.raises(CondaHTTPError) as execinfo:
                        url = "http://240.0.0.0/channel/osx-64"
                        msg = "Connection error:"
                        fetch_repodata_remote_request(url, None, None)
                        assert msg in str(execinfo)

    def test_tmpDownload(self):
        with env_var('CONDA_REMOTE_CONNECT_TIMEOUT_SECS', 1, stack_callback=conda_tests_ctxt_mgmt_def_pol):
            with env_var('CONDA_REMOTE_READ_TIMEOUT_SECS', 1, stack_callback=conda_tests_ctxt_mgmt_def_pol):
                with env_var('CONDA_REMOTE_MAX_RETRIES', 1, stack_callback=conda_tests_ctxt_mgmt_def_pol):
                    url = "https://repo.anaconda.com/pkgs/free/osx-64/appscript-1.0.1-py27_0.tar.bz2"
                    with TmpDownload(url) as dst:
                        assert exists(dst)
                        assert isfile(dst)

                    msg = "Rock and Roll Never Die"
                    with TmpDownload(msg) as result:
                        assert result == msg


class TestFetchRepoData(TestCase):
    # @responses.activate
    # def test_fetchrepodata_httperror(self):
    #     with pytest.raises(CondaHTTPError) as execinfo:
    #         url = DEFAULT_CHANNEL_ALIAS
    #         user = binstar.remove_binstar_tokens(url).split(DEFAULT_CHANNEL_ALIAS)[1].split("/")[0]
    #         msg = 'Could not find anaconda.org user %s' % user
    #         filename = 'repodata.json'
    #         responses.add(responses.GET, url+filename, body='{"error": "not found"}', status=404,
    #                       content_type='application/json')
    #
    #         fetch_repodata(url)
    #         assert msg in str(execinfo), str(execinfo)
    pass


class TestDownload(TestCase):

    @responses.activate
    def test_download_httperror(self):
        with pytest.raises(CondaHTTPError) as execinfo:
            url = DEFAULT_CHANNEL_ALIAS
            msg = "HTTPError:"
            responses.add(responses.GET, url, body='{"error": "not found"}', status=404,
                          content_type='application/json')
            download(url, mktemp())
            assert msg in str(execinfo)
