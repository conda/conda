# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Strongly related to subdir_data / test_subdir_data.
"""

from __future__ import annotations

import sys

import pytest

from conda.base.context import conda_tests_ctxt_mgmt_def_pol, context
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
    class Response:
        def __init__(self, status_code):
            self.status_code = status_code

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
        raise HTTPError(response=Response(404))

    with pytest.raises(RepodataIsEmpty), env_vars(
        {"CONDA_ALLOW_NON_CHANNEL_URLS": "1"},
        stack_callback=conda_tests_ctxt_mgmt_def_pol,
    ), conda_http_errors("https://conda.anaconda.org/noarch", "repodata.json"):
        raise HTTPError(response=Response(404))

    # A variety of helpful error messages should follow
    with pytest.raises(CondaHTTPError, match="invalid credentials"), conda_http_errors(
        "https://conda.anaconda.org/noarch", "repodata.json"
    ):
        raise HTTPError(response=Response(401))

    # A (random uuid) token should trigger a different message.
    with pytest.raises(CondaHTTPError, match="token"), conda_http_errors(
        "/t/dh-73683400-b3ee-4f87-ade8-37de6d395bdb/conda-forge/noarch", "repodata.json"
    ):
        raise HTTPError(response=Response(401))

    # env_vars plus a harmless option to reset context on exit
    with pytest.raises(CondaHTTPError, match="The credentials"), env_vars(
        {"CONDA_ALLOW_NON_CHANNEL_URLS": "1"},
        stack_callback=conda_tests_ctxt_mgmt_def_pol,
    ), conda_http_errors("https://conda.anaconda.org/noarch", "repodata.json"):
        context.channel_alias.location = "xyzzy"
        raise HTTPError(response=Response(401))

    # was the context reset properly?
    assert context.channel_alias.location != "xyzzy"

    # Oh no
    with pytest.raises(CondaHTTPError, match="A 500-type"), conda_http_errors(
        "https://repo.anaconda.com/main/linux-64", "repodata.json"
    ):
        raise HTTPError(response=Response(500))

    # Ask to unblock URL
    with pytest.raises(CondaHTTPError, match="blocked"), conda_http_errors(
        "https://repo.anaconda.com/main/linux-64", "repodata.json"
    ):
        raise HTTPError(response=Response(418))

    # Just an error
    with pytest.raises(CondaHTTPError, match="An HTTP error"), conda_http_errors(
        "https://example.org/main/linux-64", "repodata.json"
    ):
        raise HTTPError(response=Response(418))

    # Don't know how to configure "context.channel_alias not in url"


def test_ssl_unavailable_error_message():
    try:
        # OpenSSL appears to be unavailable
        with pytest.raises(CondaSSLError, match="unavailable"), conda_http_errors(
            "https://conda.anaconda.org", "repodata.json"
        ):
            sys.modules["ssl"] = None  # type: ignore
            raise SSLError()
    finally:
        del sys.modules["ssl"]
