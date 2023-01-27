# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from argparse import ArgumentParser

import pytest
from conda import plugins
from conda.plugins.types import CondaSubcommand


class SubcommandPlugin:
    def __init__(self):
        self.invoked = False
        self.args = None

    def custom_command(self, args):
        pass

    @plugins.hookimpl
    def conda_subcommands(self):
        yield CondaSubcommand(
            name="custom",
            summary="test custom command",
            action=self.custom_command,
        )


class SubcommandPluginWithCustomParser:
    """
    This version of our test subcommand does not except any values for it's
    "action" method and parses its own arguments.
    """

    def custom_command(self):
        pass

    @plugins.hookimpl
    def conda_subcommands(self):
        yield CondaSubcommand(
            name="custom",
            summary="test custom command",
            action=self.custom_command,
            no_sys_argv=True,
        )


@pytest.fixture()
def plugin(mocker, plugin_manager):
    mocker.patch.object(SubcommandPlugin, "custom_command")

    plugin = SubcommandPlugin()
    plugin_manager.register(plugin)
    return plugin


@pytest.fixture()
def plugin_with_custom_parser(mocker, plugin_manager):
    mocker.patch.object(SubcommandPluginWithCustomParser, "custom_command")

    plugin = SubcommandPluginWithCustomParser()
    plugin_manager.register(plugin)
    return plugin


def test_invoked(plugin, cli_main):
    cli_main("custom", "some-arg", "some-other-arg")

    plugin.custom_command.assert_called_with(["some-arg", "some-other-arg"])


def test_invoked_with_custom_parser(plugin_with_custom_parser, cli_main):
    """
    Makes sure that we test subcommand plugins which do not accept sys args as the
    first argument for their ``action`` command.
    """
    cli_main("custom", "some-arg", "some-other-arg")

    plugin_with_custom_parser.custom_command.assert_called_with()


def test_help(plugin, cli_main, capsys):
    cli_main("--help")

    stdout, stderr = capsys.readouterr()

    assert "custom - test custom command" in stdout


def test_duplicated(plugin_manager, cli_main, capsys):
    plugin_manager.register(SubcommandPlugin())
    plugin_manager.register(SubcommandPlugin())

    cli_main()
    stdout, stderr = capsys.readouterr()

    assert "Conflicting `subcommands` plugins found" in stderr
