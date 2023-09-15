# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pytest
from pytest import CaptureFixture
from pytest_mock import MockerFixture

from conda import plugins
from conda.auxlib.ish import dals
from conda.base.context import context
from conda.cli.conda_argparse import BUILTIN_COMMANDS, generate_parser
from conda.plugins.types import CondaSubcommand
from conda.testing import CondaCLIFixture


@dataclass(frozen=True)
class SubcommandPlugin:
    name: str
    summary: str
    configure_parser: Callable | None = None

    def custom_command(self, args):
        pass

    @plugins.hookimpl
    def conda_subcommands(self):
        yield CondaSubcommand(
            name=self.name,
            summary=self.summary,
            action=self.custom_command,
            configure_parser=self.configure_parser,
        )


def test_invoked(plugin_manager, conda_cli: CondaCLIFixture, mocker: MockerFixture):
    """Ensure we are able to invoke our command after creating it."""
    # mocks
    mocked = mocker.patch.object(SubcommandPlugin, "custom_command")

    # setup
    plugin_manager.register(SubcommandPlugin(name="custom", summary="Summary."))

    # test
    conda_cli("custom", "some-arg", "some-other-arg")

    # assertions; make sure our command was invoked with the right arguments
    mocked.assert_called_with(("some-arg", "some-other-arg"))


def test_help(plugin_manager, conda_cli: CondaCLIFixture, capsys: CaptureFixture):
    """Ensures the command appears on the help page."""
    # setup
    plugin_manager.register(SubcommandPlugin(name="custom", summary="Summary."))

    # test
    with pytest.raises(SystemExit, match="0"):
        conda_cli("--help")

    stdout, stderr = capsys.readouterr()

    # assertions; make sure our command appears with the help blurb
    assert "custom            Summary." in stdout
    assert not stderr


def test_duplicated(plugin_manager, conda_cli: CondaCLIFixture):
    """
    Ensures we get an error when attempting to register commands with the same `name` property.
    """
    # setup
    plugin = SubcommandPlugin(name="custom", summary="Summary.")
    assert plugin_manager.load_plugins(plugin) == 1

    # invalid, identical plugins
    with pytest.raises(PluginError, match="Error while loading first-party"):
        plugin_manager.load_plugins(plugin)

    # invalid, similar plugins
    plugin2 = SubcommandPlugin(name="custom", summary="Summary.")
    with pytest.raises(PluginError, match="Error while loading first-party"):
        plugin_manager.load_plugins(plugin2)


@pytest.mark.parametrize("command", BUILTIN_COMMANDS)
def test_cannot_override_builtin_commands(command, plugin_manager, mocker, conda_cli):
    """
    Ensures that plugin subcommands do not override the builtin conda commands
    """
    # mocks
    mocked = mocker.patch.object(SubcommandPlugin, "custom_command")
    mock_log = mocker.patch("conda.cli.conda_argparse.log")

    # setup
    plugin_manager.register(SubcommandPlugin(name=command, summary="Summary."))

    # test
    with pytest.raises(SystemExit, match="0"):
        conda_cli(command, "--help")

    # assertions; make sure we got the right error messages and didn't invoke the custom command
    assert mock_log.error.mock_calls == [
        mocker.call(
            dals(
                f"""
                The plugin '{command}' is trying to override the built-in command
                with the same name, which is not allowed.

                Please uninstall the plugin to stop seeing this error message.
                """
            )
        )
    ]

    assert mocked.mock_calls == []


def test_parser_no_plugins(plugin_manager):
    subcommand_plugin = SubcommandPlugin(name="custom", summary="Summary.")
    assert plugin_manager.load_plugins(subcommand_plugin) == 1
    assert plugin_manager.is_registered(subcommand_plugin)

    parser = generate_parser()

    with pytest.raises(SystemExit, match="2"):
        parser.parse_args(["foobar"])

    args = parser.parse_args(["custom"])
    assert args.cmd == "custom"

    plugin_manager.disable_external_plugins()

    parser = generate_parser()

    with pytest.raises(SystemExit, match="2"):
        parser.parse_args(["foobar"])

    with pytest.raises(SystemExit, match="2"):
        args = parser.parse_args(["custom"])


def test_custom_plugin_not_extend_parser(
    plugin_manager,
    conda_cli: CondaCLIFixture,
    mocker: MockerFixture,
):
    subcommand_plugin = SubcommandPlugin(name="custom", summary="Summary.")
    assert plugin_manager.load_plugins(subcommand_plugin) == 1
    assert plugin_manager.is_registered(subcommand_plugin)

    mocker.patch(
        "conda.base.context.Context.plugin_manager",
        return_value=plugin_manager,
        new_callable=mocker.PropertyMock,
    )
    assert context.plugin_manager is plugin_manager

    stdout, stderr, err = conda_cli("custom", "--help")
    # configure_parser is undefined and action don't do anything, so this subcommand does not have any help text
    assert not stdout
    assert not stderr
    assert not err


def test_custom_plugin_extend_parser(
    plugin_manager,
    conda_cli: CondaCLIFixture,
    mocker: MockerFixture,
):
    def configure_parser(subparser):
        pass

    subcommand_plugin = SubcommandPlugin(
        name="custom",
        summary="Summary.",
        configure_parser=configure_parser,
    )
    assert plugin_manager.load_plugins(subcommand_plugin) == 1
    assert plugin_manager.is_registered(subcommand_plugin)

    mocker.patch(
        "conda.base.context.Context.plugin_manager",
        return_value=plugin_manager,
        new_callable=mocker.PropertyMock,
    )
    assert context.plugin_manager is plugin_manager

    with pytest.raises(SystemExit, match="0"):
        conda_cli("custom", "--help")
