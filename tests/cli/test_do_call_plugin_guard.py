# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Verify that command hooks keep running during deprecation."""

from __future__ import annotations

from argparse import Namespace
from contextlib import nullcontext
from importlib import import_module

import pytest

from conda import plugins
from conda.cli.conda_argparse import do_call


@pytest.mark.parametrize(
    "module_name, deprecate",
    [
        ("main_mock_activate", True),
        ("main_mock_deactivate", True),
        ("main_run", True),
        ("main_info", False),
    ],
)
def test_builtin_command_hooks_deprecation(
    mocker, plugin_manager, module_name: str, deprecate: bool
):
    command = module_name.removeprefix("main_")
    calls = []

    class CommandPlugin:
        @plugins.hookimpl
        def conda_pre_commands(self):
            yield plugins.types.CondaPreCommand(
                name="custom-pre-command",
                action=lambda command: calls.append(("pre", command)),
                run_for={command},
            )

        @plugins.hookimpl
        def conda_post_commands(self):
            yield plugins.types.CondaPostCommand(
                name="custom-post-command",
                action=lambda command: calls.append(("post", command)),
                run_for={command},
            )

    def execute(args, parser):
        calls.append(("execute", command))
        return 0

    plugin_manager.register(CommandPlugin())
    module = import_module(f"conda.cli.{module_name}")
    mocker.patch.object(module, "execute", side_effect=execute)

    args = Namespace(func=f"conda.cli.{module_name}.execute")
    with (
        pytest.deprecated_call(match=r"will be removed in 27\.9")
        if deprecate
        else nullcontext()
    ) as warnings:
        assert do_call(args, parser=None) == 0

    if deprecate:
        assert len(warnings) == 2
    assert calls == [("pre", command), ("execute", command), ("post", command)]


@pytest.mark.parametrize(
    "command", ["hook", "reactivate", "mock_activate", "mock_deactivate"]
)
def test_plugin_subcommand_hooks_not_deprecated(plugin_manager, command):
    calls = []

    class CommandPlugin:
        @plugins.hookimpl
        def conda_pre_commands(self):
            yield plugins.types.CondaPreCommand(
                name="custom-pre-command",
                action=lambda command: calls.append(("pre", command)),
                run_for={command},
            )

        @plugins.hookimpl
        def conda_post_commands(self):
            yield plugins.types.CondaPostCommand(
                name="custom-post-command",
                action=lambda command: calls.append(("post", command)),
                run_for={command},
            )

    plugin_manager.register(CommandPlugin())
    subcommand = plugins.types.CondaSubcommand(
        name=command,
        summary="Example plugin subcommand",
        action=lambda args: calls.append(("execute", command)),
    )

    do_call(Namespace(_plugin_subcommand=subcommand), parser=None)

    assert calls == [("pre", command), ("execute", command), ("post", command)]
