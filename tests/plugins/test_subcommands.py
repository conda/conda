import re
import textwrap

import conda.exceptions
from conda import plugins

import pytest


class SubcommandPlugin:
        def __init__(self):
            self.invoked = False
            self.args = None

        def custom_command(self, args):
            pass

        @plugins.hookimp
        def conda_cli_register_subcommands(self):
            yield plugins.CondaSubcommand(
                name='custom',
                summary='test custom command',
                action=self.custom_command,
            )


@pytest.fixture()
def plugin(mocker, plugin_manager):
    mocker.patch.object(SubcommandPlugin, 'custom_command')

    plugin = SubcommandPlugin()
    plugin_manager.register(plugin)
    return plugin


def test_invoked(plugin, cli_main):
    cli_main('custom', 'some-arg', 'some-other-arg')

    plugin.custom_command.assert_called_with(['some-arg', 'some-other-arg'])


def test_help(plugin, cli_main, capsys):
    cli_main('--help')

    stdout, stderr = capsys.readouterr()

    assert textwrap.dedent('''
        conda commands available from other packages:
          custom - test custom command
    ''') in stdout


def test_duplicated(plugin_manager, cli_main, capsys):
    plugin_manager.register(SubcommandPlugin())
    plugin_manager.register(SubcommandPlugin())

    cli_main()

    stdout, stderr = capsys.readouterr()

    assert (
        'Conflicting subcommand entries found for the '
        '`custom` subcommand. Multiple Conda plugins '
        'are registering this subcommand via the '
        '`conda_cli_register_subcommands` hook, please make sure '
        'you don\'t have any incompatible plugins installed.'
    ) in stderr
