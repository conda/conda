# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from contextlib import contextmanager
from sys import stdout

import pytest

from conda import plugins
from conda.plugins.reporter_streams import plugins as default_plugins
from conda.plugins.types import CondaReporterStream


@contextmanager
def dummy_render():
    """Dummy IO that yield ``stdout``"""
    yield stdout


class OutputHandlerPlugin:
    @plugins.hookimpl
    def conda_reporter_streams(self):
        yield CondaReporterStream(
            name="dummy",
            description="Dummy output handler meant for testing",
            stream=dummy_render,
        )


@pytest.fixture()
def reporter_stream_plugin(plugin_manager):
    reporter_stream_plugin = OutputHandlerPlugin()
    plugin_manager.register(reporter_stream_plugin)

    return plugin_manager


@pytest.fixture()
def default_reporter_stream_plugin(plugin_manager):
    for plugin in default_plugins:
        plugin_manager.register(plugin)

    return plugin_manager


def test_reporter_steram_is_registered(reporter_stream_plugin):
    """
    Ensures that our dummy reporter stream has been registered
    """
    reporter_streams = reporter_stream_plugin.get_reporter_streams()

    assert "dummy" in {handler.name for handler in reporter_streams}


def test_default_reporter_stream_is_registered(default_reporter_stream_plugin):
    """
    Ensures that the default repoter stream is registered and can be used
    """
    reporter_streams = default_reporter_stream_plugin.get_reporter_streams()

    expected_defaults = {"stdout"}
    actual_defaults = {stream.name for stream in reporter_streams}

    assert expected_defaults == actual_defaults
