# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from __future__ import annotations

import logging
from contextlib import ExitStack, contextmanager
from pathlib import Path
from typing import TYPE_CHECKING
from unittest import mock

import pytest

import conda
from conda.base.constants import PkgEnvLayout
from conda.base.context import context, reset_context
from conda.common.compat import NoneType
from conda.common.configuration import (
    ParameterLoader,
    PrimitiveParameter,
    SequenceParameter,
)
from conda.core.package_cache_data import PackageCacheData
from conda.gateways.connection.session import CondaSession, get_session
from conda.plugins.hookspec import CondaSpecs
from conda.plugins.manager import CondaPluginManager
from conda.plugins.reporter_backends import plugins as reporter_backend_plugins

from . import TEST_RECIPES_CHANNEL, http_test_server

if TYPE_CHECKING:
    import http.server
    from collections.abc import Iterable, Iterator
    from typing import Callable

    from pytest_mock import MockerFixture

pytest_plugins = (
    # Add testing fixtures and internal pytest plugins here
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
    mocker.patch(
        "conda.base.context.Context.channels",
        new_callable=mocker.PropertyMock,
        return_value=(channel_str := str(TEST_RECIPES_CHANNEL),),
    )
    reset_context()
    assert context.channels == (channel_str,)

    return TEST_RECIPES_CHANNEL


@pytest.fixture
def clear_cache():
    from conda.core.subdir_data import SubdirData

    SubdirData.clear_cached_local_channel_data(exclude_file=False)


@pytest.fixture(scope="session")
def support_file_server() -> Iterable[http.server.ThreadingHTTPServer]:
    """Open a local web server to test remote support files."""
    base = Path(__file__).parents[0] / "env" / "support"
    http = http_test_server.run_test_server(str(base))
    yield http
    # shutdown is checked at a polling interval, or the daemon thread will shut
    # down when the test suite exits.
    http.shutdown()


@pytest.fixture
def support_file_server_port(
    support_file_server: http.server.ThreadingHTTPServer,
) -> int:
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


@pytest.fixture(autouse=True)
def automatically_use_conda_root_pkgs_envs(mock_context_attributes):
    """Do not notify about pkgs/ and envs/ in the root prefix during tests."""
    with mock_context_attributes(pkg_env_layout=PkgEnvLayout.CONDA_ROOT):
        yield


@pytest.fixture
def plugin_manager(mocker) -> CondaPluginManager:
    pm = CondaPluginManager()
    pm.add_hookspecs(CondaSpecs)
    mocker.patch("conda.plugins.manager.get_plugin_manager", return_value=pm)
    return pm


@pytest.fixture
def plugin_manager_with_reporter_backends(plugin_manager) -> CondaPluginManager:
    """
    Returns a ``CondaPluginManager`` with default reporter backend plugins loaded
    """
    plugin_manager.load_plugins(*reporter_backend_plugins)

    return plugin_manager


@pytest.fixture
def clear_conda_session_cache() -> Iterable[None]:
    """
    We use this to clean up the class/function cache on various things in the
    ``conda.gateways.connection.session`` module.
    """
    try:
        del CondaSession._thread_local.sessions
    except AttributeError:
        pass

    get_session.cache_clear()

    yield

    try:
        del CondaSession._thread_local.sessions
    except AttributeError:
        pass

    get_session.cache_clear()


@pytest.fixture
def clear_package_cache() -> Iterable[None]:
    PackageCacheData.clear()

    yield

    PackageCacheData.clear()


@pytest.fixture
def propagate_conda_logger():
    """A fixture which propagates the logs of the `conda` logger to the root.

    This fixture is useful when writing tests that rely on the caplog fixture to
    capture log messages.
    """
    logger = logging.getLogger("conda")
    logger.propagate = True
    yield
    logger.propagate = False


@pytest.fixture
def mock_context_attributes() -> Callable:
    """A fixture that returns a context manager for mocking the context.

    This can be used to mock attributes quickly:

        with mock_context_attributes(
            pkg_env_layout=pkg_env_layout,
            _pkgs_dirs=(pkgs,),
            _envs_dirs=(envs,),
        ):
            ...

    This context manager will iterate through each kwarg, patching each
    of the keys with the given value, and then resetting the context.
    Most simple ``Context`` attributes are handled automatically.
    """

    @contextmanager
    def mock_attribute(**kwargs) -> Iterator:
        with ExitStack() as stack:
            for key, value in kwargs.items():
                if isinstance(value, ParameterLoader):
                    param = value
                elif isinstance(value, (str, NoneType)):
                    param = ParameterLoader(
                        PrimitiveParameter(value, element_type=(str, NoneType))
                    )
                elif isinstance(value, tuple):
                    param = ParameterLoader(
                        SequenceParameter(
                            PrimitiveParameter("", element_type=str),
                            value,
                        )
                    )
                elif isinstance(value, bool):
                    param = ParameterLoader(PrimitiveParameter(value))
                else:
                    raise NotImplementedError

                param._set_name(key)
                stack.enter_context(
                    mock.patch(
                        f"conda.base.context.Context.{key}",
                        new=param,
                    )
                )
            yield

    return mock_attribute
