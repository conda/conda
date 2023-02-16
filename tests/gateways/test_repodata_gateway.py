# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Strongly related to subdir_data / test_subdir_data.
"""

from __future__ import annotations

import sys

import pytest

from conda.base.context import conda_tests_ctxt_mgmt_def_pol
from conda.common.io import env_vars
from conda.exceptions import (
    CondaDependencyError,
    CondaHTTPError,
    CondaSSLError,
    ProxyError,
    UnavailableInvalidChannel,
)
from conda.gateways.connection import HTTPError, InvalidSchema, RequestsProxyError, SSLError
from conda.gateways.repodata import RepodataIsEmpty, conda_http_errors


def test_coverage_conda_http_errors():

    with pytest.raises(ProxyError), conda_http_errors(
        "https://conda.anaconda.org", "repodata.json"
    ):
        raise RequestsProxyError()

    with pytest.raises(CondaDependencyError), conda_http_errors(
        "https://conda.anaconda.org", "repodata.json"
    ):
        raise InvalidSchema("SOCKS")

    with pytest.raises(InvalidSchema), conda_http_errors(
        "https://conda.anaconda.org", "repodata.json"
    ):
        raise InvalidSchema("shoes")  # not a SOCKS problem

    with pytest.raises(CondaSSLError), conda_http_errors(
        "https://conda.anaconda.org", "repodata.json"
    ):
        raise SSLError()

    # strange url-ends-with-noarch-specific behavior
    with pytest.raises(UnavailableInvalidChannel), conda_http_errors(
        "https://conda.anaconda.org/noarch", "repodata.json"
    ):

        class Response:
            status_code = 404

        raise HTTPError(response=Response)

    with pytest.raises(RepodataIsEmpty), env_vars(
        {"CONDA_ALLOW_NON_CHANNEL_URLS": "1"},
        stack_callback=conda_tests_ctxt_mgmt_def_pol,
    ), conda_http_errors("https://conda.anaconda.org/noarch", "repodata.json"):

        class Response:
            status_code = 404

        raise HTTPError(response=Response)

    # A variety of helpful error messages should follow
    with pytest.raises(CondaHTTPError, match="invalid credentials"), conda_http_errors(
        "https://conda.anaconda.org/noarch", "repodata.json"
    ):

        class Response:
            status_code = 401

        raise HTTPError(response=Response)

    # A (random uuid) token should trigger a different message.
    with pytest.raises(CondaHTTPError, match="token"), conda_http_errors(
        "/t/dh-73683400-b3ee-4f87-ade8-37de6d395bdb/conda-forge/noarch", "repodata.json"
    ):

        class Response:
            status_code = 401

        raise HTTPError(response=Response)

    # Oh no
    with pytest.raises(CondaHTTPError, match="A 500-type"), conda_http_errors(
        "https://repo.anaconda.com/main/linux-64", "repodata.json"
    ):

        class Response:
            status_code = 500

        raise HTTPError(response=Response)

    # Ask to unblock URL
    with pytest.raises(CondaHTTPError, match="blocked"), conda_http_errors(
        "https://repo.anaconda.com/main/linux-64", "repodata.json"
    ):

        class Response:
            status_code = 418

        raise HTTPError(response=Response)

    # Just an error
    with pytest.raises(CondaHTTPError, match="An HTTP error"), conda_http_errors(
        "https://example.org/main/linux-64", "repodata.json"
    ):

        class Response:
            status_code = 418

        raise HTTPError(response=Response)

    # Don't know how to configure "context.channel_alias not in url"


def test_ssl_unavailable_error_message():
    try:
        # OpenSSL appears to be unavailable
        with pytest.raises(CondaSSLError, match="unavailable"), conda_http_errors(
            "https://conda.anaconda.org", "repodata.json"
        ):
            sys.modules["ssl"] = None
            raise SSLError()
    finally:
        del sys.modules["ssl"]
