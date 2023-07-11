# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import pytest

from conda import plugins
from conda.plugins.types import CondaPostCommand


class PostCommandPlugin:
    def post_command_action(self, command: str, arguments) -> int:
        pass

    @plugins.hookimpl
    def conda_post_commands(self):
        yield CondaPostCommand(
            name="custom-post-command",
            action=self.post_command_action,
            run_for={"install", "create", "info"},
        )


@pytest.fixture()
def post_command_plugin(mocker, plugin_manager):
    mocker.patch.object(PostCommandPlugin, "post_command_action")

    post_command_plugin = PostCommandPlugin()
    plugin_manager.register(post_command_plugin)

    return post_command_plugin


def test_post_command_invoked(post_command_plugin, conda_cli):
    """
    Makes sure that we successfully invoked our "post-command" action.
    """
    conda_cli("info")

    assert len(post_command_plugin.post_command_action.mock_calls) == 1


def test_post_command_not_invoked(post_command_plugin, conda_cli):
    """
    Makes sure that we successfully did not invoke our "post-command" action.
    """
    conda_cli("config")

    assert len(post_command_plugin.post_command_action.mock_calls) == 0


def test_post_command_action_raises_exception(post_command_plugin, conda_cli):
    """
    When the plugin action fails or raises an exception, we want to make sure
    that it bubbles up to the top and isn't caught anywhere. This will ensure that it
    goes through our normal exception catching/reporting mechanism.
    """
    exc_message = "💥"
    post_command_plugin.post_command_action.side_effect = [Exception(exc_message)]

    with pytest.raises(Exception, match=exc_message):
        conda_cli("info")

    assert len(post_command_plugin.post_command_action.mock_calls) == 1
