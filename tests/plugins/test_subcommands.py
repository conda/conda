# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest

from conda import plugins
from conda.auxlib.ish import dals
from conda.base.context import context
from conda.cli.conda_argparse import (
    _PLUGIN_FREE_BUILTIN_COMMANDS,
    BUILTIN_COMMANDS,
    find_builtin_commands,
    generate_parser,
)
from conda.plugins.types import CondaSubcommand

if TYPE_CHECKING:
    from collections.abc import Callable

    from pytest import CaptureFixture
    from pytest_mock import MockerFixture

    from conda.testing.fixtures import CondaCLIFixture


@dataclass(frozen=True)
class SubcommandPlugin:
    name: str
    summary: str
    aliases: str | tuple[str, ...] = ()
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
            aliases=self.aliases,
        )


@pytest.fixture
def alias_overlap_log_call(mocker):
    def log_call(plugin_name, aliases):
        return mocker.call(
            dals(
                f"""
                The plugin '{plugin_name}' is trying to register aliases that overlap
                with existing conda commands: {aliases}

                Please uninstall the plugin to stop seeing this error message.
                """
            )
        )

    return log_call


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


@pytest.mark.parametrize(
    "aliases",
    (("alternate",), "alternate"),
    ids=("tuple-alias", "string-alias"),
)
def test_alias_invoked(
    aliases,
    plugin_manager,
    conda_cli: CondaCLIFixture,
    mocker: MockerFixture,
):
    """Ensure plugin subcommand aliases invoke the command."""
    mocked = mocker.patch.object(SubcommandPlugin, "custom_command")
    plugin_manager.register(
        SubcommandPlugin(name="custom", summary="Summary.", aliases=aliases)
    )

    conda_cli("alternate", "some-arg")

    mocked.assert_called_with(("some-arg",))


def test_help(plugin_manager, conda_cli: CondaCLIFixture, capsys: CaptureFixture):
    """Ensures the command appears on the help page."""
    # setup
    plugin_manager.register(SubcommandPlugin(name="custom", summary="Summary."))

    # test
    with pytest.raises(SystemExit, match="0"):
        conda_cli("--help")

    stdout, stderr = capsys.readouterr()

    # assertions; make sure our command appears with the help blurb
    assert re.search(r"custom\s+Summary.", stdout) is not None
    assert not stderr


def test_alias_help(plugin_manager, conda_cli: CondaCLIFixture, capsys: CaptureFixture):
    """Ensures aliases appear on the help page."""
    plugin_manager.register(
        SubcommandPlugin(name="custom", summary="Summary.", aliases=("alternate",))
    )

    with pytest.raises(SystemExit, match="0"):
        conda_cli("--help")

    stdout, stderr = capsys.readouterr()

    assert re.search(r"custom \(alternate\)\s+Summary.", stdout) is not None
    assert not stderr


def test_alias_commands(plugin_manager, conda_cli: CondaCLIFixture):
    """Ensures aliases appear in the command discovery output."""
    plugin_manager.register(
        SubcommandPlugin(name="custom", summary="Summary.", aliases=("alternate",))
    )

    stdout, stderr, code = conda_cli("commands")

    assert code == 0, f"conda commands failed ({code}): {stderr}"
    assert {"custom", "alternate"}.issubset(stdout.splitlines())
    assert not stderr


def test_duplicated(plugin_manager, conda_cli: CondaCLIFixture):
    """
    Ensures we get an error when attempting to register commands with the same `name` property.
    """
    # setup
    plugin = SubcommandPlugin(name="custom", summary="Summary.")
    assert plugin_manager.load_plugins(plugin) == 1

    # invalid, identical plugins, error ignored
    assert plugin_manager.load_plugins(plugin) == 0

    # invalid, similar plugins, error ignored
    plugin2 = SubcommandPlugin(name="custom", summary="Summary.")
    assert plugin_manager.load_plugins(plugin2) == 0


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
    expected_log_calls = (
        []
        if command in _PLUGIN_FREE_BUILTIN_COMMANDS
        else [
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
    )
    assert mock_log.error.mock_calls == expected_log_calls

    assert mocked.mock_calls == []


@pytest.mark.parametrize("command", BUILTIN_COMMANDS)
def test_alias_cannot_override_builtin_commands(
    command, plugin_manager, mocker, alias_overlap_log_call
):
    """Ensures plugin subcommand aliases do not override built-in commands."""
    mock_log = mocker.patch("conda.cli.conda_argparse.log")
    plugin_manager.register(
        SubcommandPlugin(name="custom", summary="Summary.", aliases=(command,))
    )

    parser = generate_parser()

    assert "custom" not in find_builtin_commands(parser)
    assert mock_log.error.mock_calls == [alias_overlap_log_call("custom", command)]


@pytest.mark.parametrize(
    ("subcommand_plugins", "registered_commands", "expected_log_calls"),
    (
        pytest.param(
            (
                SubcommandPlugin(
                    name="custom",
                    summary="Summary.",
                    aliases=("other",),
                ),
                SubcommandPlugin(name="other", summary="Other summary."),
            ),
            {"other"},
            (("custom", "other"),),
            id="alias-matches-plugin-subcommand",
        ),
        pytest.param(
            (
                SubcommandPlugin(
                    name="custom",
                    summary="Summary.",
                    aliases=("alternate",),
                ),
                SubcommandPlugin(
                    name="other",
                    summary="Other summary.",
                    aliases=("alternate",),
                ),
            ),
            set(),
            (("custom", "alternate"), ("other", "alternate")),
            id="shared-alias",
        ),
    ),
)
def test_alias_cannot_overlap_plugin_subcommands(
    subcommand_plugins,
    registered_commands,
    expected_log_calls,
    plugin_manager,
    mocker,
    alias_overlap_log_call,
):
    """Ensures aliases do not overlap with plugin subcommands or aliases."""
    mock_log = mocker.patch("conda.cli.conda_argparse.log")
    for subcommand_plugin in subcommand_plugins:
        plugin_manager.register(subcommand_plugin)

    parser = generate_parser()
    commands = set(find_builtin_commands(parser))

    assert commands & {"custom", "other"} == registered_commands
    assert mock_log.error.mock_calls == [
        alias_overlap_log_call(plugin_name, aliases)
        for plugin_name, aliases in expected_log_calls
    ]


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


def test_custom_plugin_extend_parser_alias(
    plugin_manager,
    conda_cli: CondaCLIFixture,
    mocker: MockerFixture,
):
    def configure_parser(subparser):
        subparser.add_argument("--flag", action="store_true")

    mocked = mocker.patch.object(SubcommandPlugin, "custom_command")
    subcommand_plugin = SubcommandPlugin(
        name="custom",
        summary="Summary.",
        aliases=("alternate",),
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

    conda_cli("alternate", "--flag")

    args = mocked.call_args.args[0]
    assert args.flag is True
