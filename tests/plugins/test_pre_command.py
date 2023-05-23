# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from unittest import mock

import pytest

from conda import plugins
from conda.plugins.types import CondaPreCommand


class PreCommandPlugin:
    def __init__(self):
        self.invoked = False
        self.args = None

    def pre_command_action(self) -> int:
        pass

    @plugins.hookimpl
    def conda_pre_commands(self):
        yield CondaPreCommand(
            name="custom_pre_run",
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
