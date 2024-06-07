# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from contextlib import contextmanager
from sys import stdout

import pytest

from conda import plugins
from conda.plugins.reporter_outputs import plugins as default_plugins
from conda.plugins.types import CondaReporterOutput


@contextmanager
def dummy_render():
    """Dummy IO that yield ``stdout``"""
    yield stdout


class OutputHandlerPlugin:
    @plugins.hookimpl
    def conda_reporter_outputs(self):
        yield CondaReporterOutput(
            name="dummy",
            description="Dummy output handler meant for testing",
            stream=dummy_render,
        )


@pytest.fixture()
def reporter_output_plugin(plugin_manager):
    reporter_output_plugin = OutputHandlerPlugin()
    plugin_manager.register(reporter_output_plugin)

    return plugin_manager


@pytest.fixture()
def default_reporter_output_plugin(plugin_manager):
    for plugin in default_plugins:
        plugin_manager.register(plugin)

    return plugin_manager


def test_reporter_steram_is_registered(reporter_output_plugin):
    """
    Ensures that our dummy reporter stream has been registered
    """
    reporter_outputs = reporter_output_plugin.get_reporter_outputs()

    assert "dummy" in {handler.name for handler in reporter_outputs}


def test_default_reporter_output_is_registered(default_reporter_output_plugin):
    """
    Ensures that the default reporter stream is registered and can be used
    """
    reporter_outputs = default_reporter_output_plugin.get_reporter_outputs()

    expected_defaults = {"stdout"}
    actual_defaults = {stream.name for stream in reporter_outputs}

    assert expected_defaults == actual_defaults
