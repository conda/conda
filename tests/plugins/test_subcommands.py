# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import pytest

from conda import plugins
from conda.auxlib.ish import dals
from conda.cli.conda_argparse import BUILTIN_COMMANDS
from conda.plugins.types import CondaSubcommand
from conda.testing.helpers import run_inprocess_conda_command as run


class SubcommandPlugin:
    def __init__(self, name: str = "custom", summary: str = "test custom command"):
        self.invoked = False
        self.args = None
        self.name = name
        self.summary = summary

    def custom_command(self, args):
        pass

    @plugins.hookimpl
    def conda_subcommands(self):
        yield CondaSubcommand(
            name=self.name,
            summary=self.summary,
            action=self.custom_command,
        )


@pytest.fixture()
def plugin(mocker, plugin_manager):
    mocker.patch.object(SubcommandPlugin, "custom_command")

    plugin = SubcommandPlugin()
    plugin_manager.register(plugin)
    return plugin


def test_invoked(plugin, cli_main):
    """Ensure we are able to invoke our command after creating it."""
    cli_main("custom", "some-arg", "some-other-arg")

    plugin.custom_command.assert_called_with(("some-arg", "some-other-arg"))


def test_help(plugin, cli_main, capsys):
    """Ensures the command appears on the help page."""
    cli_main("--help")

    stdout, stderr = capsys.readouterr()

    assert "custom - test custom command" in stdout


def test_duplicated(plugin_manager, cli_main, capsys):
    """Ensures we get an error when attempting to register commands with the same `name` property."""
    plugin_manager.register(SubcommandPlugin())
    plugin_manager.register(SubcommandPlugin())

    cli_main()
    stdout, stderr = capsys.readouterr()

    assert "Conflicting `subcommands` plugins found" in stderr


@pytest.mark.parametrize("builtin_command", BUILTIN_COMMANDS)
def test_cannot_override_builtin_commands(builtin_command, plugin_manager, mocker):
    """
    Ensures that plugin subcommands do not override the builtin conda commands
    """
    # mocks
    mocker.patch.object(SubcommandPlugin, "custom_command")
    mock_log = mocker.patch("conda.cli.conda_argparse.log")

    # setup
    command_summary = "Command summary"
    plugin = SubcommandPlugin(name=builtin_command, summary=command_summary)
    expected_error = dals(
        f"The plugin '{builtin_command}: {command_summary}' is trying "
        f"to override the built-in command {builtin_command}, which is not allowed. "
        "Please uninstall this plugin to stop seeing this error message"
    )
    plugin_manager.register(plugin)

    # run code under test
    run(f"conda {builtin_command} --help")

    # assertions; make sure we got the right error messages and didn't invoke the custom command
    assert mock_log.error.mock_calls == [mocker.call(expected_error)]

    assert plugin.custom_command.mock_calls == []
