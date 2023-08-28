# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import subprocess
from pathlib import Path

import pytest
from pytest import MonkeyPatch

from conda.base.context import context, reset_context
from conda.testing import conda_cli, path_factory, tmp_env
from conda.testing.solver_helpers import parametrized_solver_fixture

from . import http_test_server
from .fixtures_jlap import (  # NOQA
    package_repository_base,
    package_server,
    package_server_ssl,
)

pytest_plugins = (
    # Add testing fixtures and internal pytest plugins here
    "conda.testing.gateways.fixtures",
    "conda.testing.notices.fixtures",
    "conda.testing.fixtures",
)

TEST_RECIPES_CHANNEL = str(Path(__file__).resolve().parent / "test-recipes")


@pytest.fixture
def test_recipes_channel(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("CONDA_BLD_PATH", TEST_RECIPES_CHANNEL)
    reset_context()
    assert context.bld_path == TEST_RECIPES_CHANNEL


@pytest.fixture
def clear_cache():
    from conda.core.subdir_data import SubdirData

    SubdirData.clear_cached_local_channel_data(exclude_file=False)


@pytest.fixture(scope="session")
def support_file_server():
    """Open a local web server to test remote support files."""
    base = Path(__file__).parents[0] / "conda_env" / "support"
    http = http_test_server.run_test_server(str(base))
    yield http
    # shutdown is checked at a polling interval, or the daemon thread will shut
    # down when the test suite exits.
    http.shutdown()


@pytest.fixture
def support_file_server_port(support_file_server):
    return support_file_server.socket.getsockname()[1]


@pytest.fixture
def clear_cuda_version():
    from conda.plugins.virtual_packages import cuda

    cuda.cached_cuda_version.cache_clear()
