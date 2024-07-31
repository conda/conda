# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

import conda
from conda.base.context import context, reset_context

from . import http_test_server

pytest_plugins = (
    # Add testing fixtures and internal pytest plugins here
    "conda.testing",
    "conda.testing.gateways.fixtures",
    "conda.testing.notices.fixtures",
    "conda.testing.fixtures",
    "tests.fixtures_jlap",
)


@pytest.hookimpl
def pytest_report_header(config: pytest.Config):
    # ensuring the expected development conda is being run
    expected = Path(__file__).parent.parent / "conda" / "__init__.py"
    assert expected.samefile(conda.__file__)
    return f"conda.__file__: {conda.__file__}"


@pytest.fixture
def test_recipes_channel(mocker: MockerFixture) -> Path:
    channel = Path(__file__).parent / "test-recipes"

    mocker.patch(
        "conda.base.context.Context.channels",
        new_callable=mocker.PropertyMock,
        return_value=(channel_str := str(channel),),
    )
    reset_context()
    assert context.channels == (channel_str,)

    return channel


@pytest.fixture
def clear_cache():
    from conda.core.subdir_data import SubdirData

    SubdirData.clear_cached_local_channel_data(exclude_file=False)


@pytest.fixture(scope="session")
def support_file_server():
    """Open a local web server to test remote support files."""
    base = Path(__file__).parents[0] / "env" / "support"
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


@pytest.fixture(autouse=True)
def do_not_register_envs(monkeypatch):
    """Do not register environments created during tests"""
    monkeypatch.setenv("CONDA_REGISTER_ENVS", "false")


@pytest.fixture(autouse=True)
def do_not_notify_outdated_conda(monkeypatch):
    """Do not notify about outdated conda during tests"""
    monkeypatch.setenv("CONDA_NOTIFY_OUTDATED_CONDA", "false")
