# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import pytest

from conda import plugins
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


def test_reporter_handler_is_register(output_handler_plugin):
    """
    Ensures that our dummy output handler has been registered
    """
    output_handlers = output_handler_plugin.get_output_handlers()

    assert "dummy" in {handler.name for handler in output_handlers}
