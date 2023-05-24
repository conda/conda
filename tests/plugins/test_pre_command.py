# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from unittest import mock

import pytest

from conda import plugins
from conda.plugins.types import CondaPreCommand

PLUGIN_NAME = "custom_pre_command"


class PreCommandPlugin:
    def __init__(self):
        self.invoked = False
        self.args = None

    def pre_command_action(self) -> int:
        pass

    @plugins.hookimpl
    def conda_pre_commands(self):
        yield CondaPreCommand(
            name=PLUGIN_NAME,
            action=self.pre_command_action,
            run_for={"install", "create", "info"},
        )


@pytest.fixture()
def pre_command_plugin(mocker, plugin_manager):
    mocker.patch.object(PreCommandPlugin, "pre_command_action")

    pre_command_plugin = PreCommandPlugin()
    plugin_manager.register(pre_command_plugin)

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
    conda_cli("list")

    assert len(pre_command_plugin.pre_command_action.mock_calls) == 0


def test_pre_command_action_raises_exception(pre_command_plugin, conda_cli, mocker):
    """
    When the plugin action fails or raises an exception, we want to make sure
    that it doesn't interrupt the normal flow of the normal command. Instead,
    we simply log an error and continue on.
    """
    mock_log = mocker.patch("conda.plugins.manager.log.error")
    exc_message = "Boom!"
    pre_command_plugin.pre_command_action.side_effect = [Exception(exc_message)]

    conda_cli("info")

    assert len(pre_command_plugin.pre_command_action.mock_calls) == 1
    assert len(mock_log.mock_calls) == 1
    assert mock_log.mock_calls[0].args == (
        f'Pre-command action for the plugin "{PLUGIN_NAME}" failed with: Exception: {exc_message}',
    )
