# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Tests for the fix tasks plugin hook."""

import pytest

from conda import plugins
from conda.plugins.subcommands import fix
from conda.plugins.types import CondaFixTask


class FixTaskPlugin:
    """Test plugin that provides a fix task."""

    def __init__(self):
        self.execute_called = False
        self.execute_args = None

    def configure_parser(self, parser):
        parser.add_argument("--test-option", action="store_true")

    def execute(self, args):
        self.execute_called = True
        self.execute_args = args
        return 0

    @plugins.hookimpl
    def conda_fix_tasks(self):
        yield CondaFixTask(
            name="test-fix",
            summary="A test fix task",
            configure_parser=self.configure_parser,
            execute=self.execute,
        )


@pytest.fixture
def plugin_manager_with_fix(plugin_manager_with_reporter_backends):
    """Register the `conda fix` subcommand."""
    plugin_manager_with_reporter_backends.load_plugins(fix)
    return plugin_manager_with_reporter_backends


@pytest.fixture
def fix_task_plugin(plugin_manager_with_fix):
    """Register a test fix task plugin."""
    fix_task_plugin = FixTaskPlugin()
    plugin_manager_with_fix.register(fix_task_plugin)
    return fix_task_plugin


def test_fix_task_registered(fix_task_plugin, plugin_manager_with_fix):
    """Test that the fix task is properly registered."""
    tasks = plugin_manager_with_fix.get_fix_tasks()

    assert "test-fix" in tasks
    assert tasks["test-fix"].summary == "A test fix task"


def test_fix_task_listed(fix_task_plugin, conda_cli):
    """Test that registered fix tasks appear in --list output."""
    out, err, code = conda_cli("fix", "--list")

    assert "test-fix" in out
    assert "A test fix task" in out
    assert not code


def test_fix_task_executed(fix_task_plugin, conda_cli):
    """Test that fix tasks are executed when invoked."""
    out, err, code = conda_cli("fix", "test-fix")

    assert fix_task_plugin.execute_called
    assert not code


def test_fix_task_receives_args(fix_task_plugin, conda_cli):
    """Test that fix tasks receive parsed arguments."""
    conda_cli("fix", "test-fix", "--test-option")

    assert fix_task_plugin.execute_called
    assert fix_task_plugin.execute_args.test_option is True


def test_fix_task_not_executed_on_other_commands(fix_task_plugin, conda_cli):
    """Test that fix tasks are not executed on unrelated commands."""
    conda_cli("info")

    assert not fix_task_plugin.execute_called

