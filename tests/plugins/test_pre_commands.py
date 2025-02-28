# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import pytest

from conda import plugins
from conda.plugins.reporter_backends import plugins as reporter_backends_plugins
from conda.plugins.types import CondaPreCommand


class PreCommandPlugin:
    def pre_command_action(self, command: str) -> None:
        pass

    @plugins.hookimpl
    def conda_pre_commands(self):
        yield CondaPreCommand(
            name="custom-pre-command",
            action=self.pre_command_action,
            run_for={"install", "create", "info"},
        )


@pytest.fixture()
def pre_command_plugin(mocker, plugin_manager):
    mocker.patch.object(PreCommandPlugin, "pre_command_action")

    pre_command_plugin = PreCommandPlugin()
    plugin_manager.register(pre_command_plugin)
    plugin_manager.load_plugins(*reporter_backends_plugins)

    return pre_command_plugin


def test_pre_command_invoked(pre_command_plugin, conda_cli):
    """
    Makes sure that we successfully invoked our "pre-command" action.
    """
    conda_cli("info")

    assert len(pre_command_plugin.pre_command_action.mock_calls) == 1


def test_pre_command_not_invoked(pre_command_plugin, conda_cli):
    """
    Makes sure that we successfully did not invoke our "pre-command" action.
    """
    conda_cli("config")

    assert len(pre_command_plugin.pre_command_action.mock_calls) == 0


def test_pre_command_action_raises_exception(pre_command_plugin, conda_cli):
    """
    When the plugin action fails or raises an exception, we want to make sure
    that it bubbles up to the top and isn't caught anywhere. This will ensure that it
    goes through our normal exception catching/reporting mechanism.
    """
    exc_message = "💥"
    pre_command_plugin.pre_command_action.side_effect = [Exception(exc_message)]

    with pytest.raises(Exception, match=exc_message):
        conda_cli("info")

    assert len(pre_command_plugin.pre_command_action.mock_calls) == 1
