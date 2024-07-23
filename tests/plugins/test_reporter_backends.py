# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import pytest

from conda import plugins
from conda.plugins.reporter_backends import plugins as default_plugins
from conda.plugins.types import CondaReporterBackend, ReporterRendererBase


class DummyReporterRenderer(ReporterRendererBase):
    """Dummy reporter backend class only for tests"""

    def detail_view(self, data: dict[str, str | int | bool], **kwargs) -> str:
        return str(data)

    def envs_list(self, data, **kwargs) -> str:
        return str(data)


class ReporterBackendPlugin:
    @plugins.hookimpl
    def conda_reporter_backends(self):
        yield CondaReporterBackend(
            name="dummy",
            description="Dummy reporter backend meant for testing",
            renderer=DummyReporterRenderer,
        )


@pytest.fixture()
def dummy_reporter_backend_plugin(plugin_manager):
    reporter_backend_plugin = ReporterBackendPlugin()
    plugin_manager.register(reporter_backend_plugin)

    return plugin_manager


@pytest.fixture()
def default_reporter_backend_plugin(plugin_manager):
    for reporter_plugin in default_plugins:
        plugin_manager.register(reporter_plugin)

    return plugin_manager


def test_dummy_reporter_backend_is_registered(dummy_reporter_backend_plugin):
    """
    Ensures that our dummy reporter backend has been registered
    """
    reporter_backends = dummy_reporter_backend_plugin.get_reporter_backends()

    assert "dummy" in {backend.name for backend in reporter_backends}


def test_default_reporter_backends_are_registered(default_reporter_backend_plugin):
    """
    Ensures that our default reporter backends have been registered
    """
    reporter_backends = default_reporter_backend_plugin.get_reporter_backends()

    expected_defaults = {"console", "json"}
    actual_defaults = {backend.name for backend in reporter_backends}

    assert expected_defaults == actual_defaults


@pytest.mark.parametrize(
    "method,backend,argument,expected",
    [
        ("render", "console", "test", "test"),
        ("render", "json", "test", '"test"'),
        ("detail_view", "console", {"test": "something"}, "\n test : something\n\n"),
        ("detail_view", "json", {"test": "something"}, '{\n  "test": "something"\n}'),
    ],
)
def test_console_reporter_backend(
    default_reporter_backend_plugin, method, backend, argument, expected
):
    """
    Ensures that the console reporter backend behaves as expected
    """
    console = default_reporter_backend_plugin.get_reporter_backend(backend)

    renderer = console.renderer()

    output = getattr(renderer, method)(argument)

    assert output == expected
