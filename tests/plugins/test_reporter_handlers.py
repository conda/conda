# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from types import SimpleNamespace

import pytest

from conda import plugins
from conda.plugins.reporter_handlers import plugins as default_plugins
from conda.plugins.types import CondaReporterHandler, ReporterHandlerBase


class DummyReporterHandler(ReporterHandlerBase):
    """Dummy reporter handler class only for tests"""

    def detail_view(self, data: dict[str, str | int | bool], **kwargs) -> str:
        return str(data)

    def envs_list(self, data, **kwargs) -> str:
        return str(data)


class ReporterHandlerPlugin:
    @plugins.hookimpl
    def conda_reporter_handlers(self):
        yield CondaReporterHandler(
            name="dummy",
            description="Dummy reporter handler meant for testing",
            handler=DummyReporterHandler(),
        )


@pytest.fixture()
def dummy_reporter_handler_plugin(plugin_manager):
    reporter_handler_plugin = ReporterHandlerPlugin()
    plugin_manager.register(reporter_handler_plugin)

    return plugin_manager


@pytest.fixture()
def default_reporter_handler_plugin(plugin_manager):
    for reporter_plugin in default_plugins:
        plugin_manager.register(reporter_plugin)

    return plugin_manager


def test_dummy_reporter_handler_is_registered(dummy_reporter_handler_plugin):
    """
    Ensures that our dummy reporter handler has been registered
    """
    reporter_handlers = dummy_reporter_handler_plugin.get_reporter_handlers()

    assert "dummy" in {handler.name for handler in reporter_handlers}


def test_default_reporter_handlers_are_registered(default_reporter_handler_plugin):
    """
    Ensures that our default reporter handlers have been registered
    """
    reporter_handlers = default_reporter_handler_plugin.get_reporter_handlers()

    expected_defaults = {"console", "json"}
    actual_defaults = {handler.name for handler in reporter_handlers}

    assert expected_defaults == actual_defaults


EXPECTED_CONSOLE_ENVS_LIST = """
# conda environments:
#
                         /tmp/test

"""


@pytest.mark.parametrize(
    "method,handler,argument,expected",
    [
        ("envs_list", "console", ["/tmp/test"], EXPECTED_CONSOLE_ENVS_LIST),
        ("envs_list", "json", ["/tmp/test"], '{\n  "envs": [\n    "/tmp/test"\n  ]\n}'),
        ("detail_view", "console", {"test": "something"}, "\n test : something\n\n"),
        ("detail_view", "json", {"test": "something"}, '{\n  "test": "something"\n}'),
    ],
)
def test_console_reporter_handler(
    default_reporter_handler_plugin, method, handler, argument, expected
):
    """
    Ensures that the console reporter handler behaves as expected
    """
    mock_context = SimpleNamespace(
        active_prefix="/tmp/active", root_prefix="/tmp/root", envs_dirs="/tmp/envs"
    )

    reporter = default_reporter_handler_plugin.get_reporter_handler(handler)

    output = getattr(reporter.handler, method)(argument, context=mock_context)

    assert output == expected
