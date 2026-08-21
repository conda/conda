# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Verify that plugin-free built-in commands do not invoke command hooks."""

from __future__ import annotations

from argparse import Namespace
from importlib import import_module

import pytest

from conda.base.context import context
from conda.cli.conda_argparse import do_call


@pytest.mark.parametrize(
    "module_name",
    ("main_mock_activate", "main_mock_deactivate", "main_run"),
)
def test_plugin_free_builtin_commands_skip_hooks(mocker, module_name: str) -> None:
    module = import_module(f"conda.cli.{module_name}")
    execute = mocker.patch.object(module, "execute", return_value=0)
    pre_command = mocker.spy(context.plugin_manager, "invoke_pre_commands")
    post_command = mocker.spy(context.plugin_manager, "invoke_post_commands")

    args = Namespace(func=f"conda.cli.{module_name}.execute")
    assert do_call(args, parser=None) == 0

    execute.assert_called_once_with(args, None)
    pre_command.assert_not_called()
    post_command.assert_not_called()
