# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

import conda
from conda.base.context import context, reset_context
from conda.common.configuration import (
    Configuration,
    ParameterLoader,
    PrimitiveParameter,
)
from conda.core.package_cache_data import PackageCacheData
from conda.gateways.connection.session import CondaSession, get_session
from conda.plugins.config import PluginConfig
from conda.plugins.hookspec import CondaSpecs
from conda.plugins.manager import CondaPluginManager
from conda.plugins.reporter_backends import plugins as reporter_backend_plugins

from . import TEST_RECIPES_CHANNEL, http_test_server

if TYPE_CHECKING:
    import http.server
    from collections.abc import Iterable

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
def support_file_isolated(tmp_path):
    """
    Copy support files to temporary path, avoid polluting source checkout.
    """
    source = Path(__file__).parents[0] / "env" / "support"
    base = tmp_path / "support"
    if not base.exists():  # tmp_path is session scoped
        shutil.copytree(source, base)

    def inner(path):
        return base / path

    return inner


@pytest.fixture
def clear_cuda_version() -> None:
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


@pytest.fixture(scope="function")
def plugin_config(mocker) -> tuple[type[Configuration], str]:
    """
    Fixture to create a plugin configuration class that can be created and used in tests
    """
    app_name = "TEST_APP_NAME"

    class PluginTest(PluginConfig):
        def get_descriptions(self) -> dict[str, str]:
            return {"bar": "Test plugins.bar"}

    PluginTest.add_plugin_setting("bar", PrimitiveParameter(""))

    class MockContext(Configuration):
        foo = ParameterLoader(PrimitiveParameter(""))
        json = ParameterLoader(PrimitiveParameter(False))

        def __init__(self, *args, **kwargs):
            """
            Defines the bare minimum of context object properties to be compatible with the
            rest of conda.

            TODO: Depending on how this fixture is used, we may need to add more properties
            """
            super().__init__(**kwargs)
            self._set_env_vars(app_name)
            self.no_plugins = False
            self.log_level = logging.WARNING
            self.active_prefix = ""
            self.plugin_manager = mocker.MagicMock()
            self.repodata_fns = ["repodata.json", "current_repodata.json"]
            self.subdir = mocker.MagicMock()

        @property
        def plugins(self) -> PluginConfig:
            return PluginTest(self.raw_data)

        def get_descriptions(self) -> dict[str, str]:
            return {
                "foo": "Test foo",
                "json": "Test json",
            }

    return MockContext, app_name


@pytest.fixture(scope="function")
def minimal_env(tmp_path: Path) -> Path:
    """
    Provides a minimal environment that only contains the "magic" file identifying it as a
    conda environment.
    """
    meta_dir = tmp_path.joinpath("conda-meta")
    meta_dir.mkdir()
    (meta_dir / "history").touch()

    return tmp_path
