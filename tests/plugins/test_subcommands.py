# SPDX-FileCopyrightText: © 2012 Continuum Analytics, Inc. <http://continuum.io>
# SPDX-FileCopyrightText: © 2017 Anaconda, Inc. <https://www.anaconda.com>
# SPDX-License-Identifier: BSD-3-Clause
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


@pytest.fixture()
def plugin(mocker, plugin_manager):
    mocker.patch.object(SubcommandPlugin, "custom_command")

    plugin = SubcommandPlugin()
    plugin_manager.register(plugin)
    return plugin


def test_invoked(plugin, cli_main):
    cli_main("custom", "some-arg", "some-other-arg")

    plugin.custom_command.assert_called_with(["some-arg", "some-other-arg"])


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
