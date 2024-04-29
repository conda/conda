# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import pytest

from conda import plugins
from conda.plugins.output_handlers import plugins as default_plugins
from conda.plugins.types import CondaOutputHandler


def dummy_render(renderable: str, **kwargs) -> None:
    """Dummy render function that just uses the print statement"""
    print(renderable)


class OutputHandlerPlugin:
    @plugins.hookimpl
    def conda_output_handlers(self):
        yield CondaOutputHandler(
            name="dummy",
            description="Dummy output handler meant for testing",
            render=dummy_render,
        )


@pytest.fixture()
def output_handler_plugin(plugin_manager):
    output_handler_plugin = OutputHandlerPlugin()
    plugin_manager.register(output_handler_plugin)

    return plugin_manager


@pytest.fixture()
def default_output_handler_plugin(plugin_manager):
    for output_handler_plugin in default_plugins:
        plugin_manager.register(output_handler_plugin)

    return plugin_manager


def get_output_handler(
    name: str, output_handlers: tuple[CondaOutputHandler, ...]
) -> CondaOutputHandler | None:
    """
    Utility function to retrieve a single output handler
    """
    for handler in output_handlers:
        if handler.name == name:
            return handler


def test_output_handler_is_registered(output_handler_plugin):
    """
    Ensures that our dummy output handler has been registered
    """
    output_handlers = output_handler_plugin.get_output_handlers()

    assert "dummy" in {handler.name for handler in output_handlers}


def test_default_output_handler_is_registered(default_output_handler_plugin):
    """
    Ensures that the default output handler is registered and can be used
    """
    output_handlers = default_output_handler_plugin.get_output_handlers()

    expected_defaults = {"stdout"}
    actual_defaults = {handler.name for handler in output_handlers}

    assert expected_defaults == actual_defaults
