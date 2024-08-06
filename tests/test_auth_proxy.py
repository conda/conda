# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import os

import pytest

from conda.base.context import context, reset_context


@pytest.mark.skipif(
    not os.getenv("CONDA_RUN_AUTH_PROXY_TEST"), reason="test not applicable"
)
def test_auth_proxy(conda_cli):
    """
    Simple test to make a request through an authenticated proxy
    """
    squid_proxy_host = os.getenv("CONDA_SQUID_PROXY_HOST", "localhost")
    squid_proxy_port = os.getenv("CONDA_SQUID_PROXY_PORT", "8118")
    squid_proxy_user = os.getenv("CONDA_SQUID_PROXY_USER", "admin")
    squid_proxy_pass = os.getenv("CONDA_SQUID_PROXY_PASS", "admin")

    context.proxy_servers = {
        "https": f"http://{squid_proxy_user}:{squid_proxy_pass}@{squid_proxy_host}:{squid_proxy_port}",
        "http": f"http://{squid_proxy_user}:{squid_proxy_pass}@{squid_proxy_host}:{squid_proxy_port}",
    }

    out, err, errno = conda_cli("search", "python")

    assert out
    assert not err

    reset_context()
