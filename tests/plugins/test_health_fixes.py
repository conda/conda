# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Tests for the conda health fixes plugin hook."""

import pytest

from conda import plugins
from conda.cli.helpers import add_output_and_prompt_options
from conda.plugins.subcommands import fix
from conda.plugins.types import CondaHealthFix


class HealthFixPlugin:
    """Test plugin that provides a health fix."""

    def __init__(self):
        self.execute_called = False
        self.execute_args = None

    def configure_parser(self, parser):
        parser.add_argument("--test-option", action="store_true")
        add_output_and_prompt_options(parser)

    def execute(self, args):
        self.execute_called = True
        self.execute_args = args
        return 0

    @plugins.hookimpl
    def conda_health_fixes(self):
        yield CondaHealthFix(
            name="test-fix",
            summary="A test health fix",
            configure_parser=self.configure_parser,
            execute=self.execute,
        )


@pytest.fixture
def plugin_manager_with_fix(plugin_manager_with_reporter_backends):
    """Register the `conda fix` subcommand."""
    plugin_manager_with_reporter_backends.load_plugins(fix)
    return plugin_manager_with_reporter_backends


@pytest.fixture
def health_fix_plugin(plugin_manager_with_fix):
    """Register a test health fix plugin."""
    health_fix_plugin = HealthFixPlugin()
    plugin_manager_with_fix.register(health_fix_plugin)
    return health_fix_plugin


def test_health_fix_registered(health_fix_plugin, plugin_manager_with_fix):
    """Test that the health fix is properly registered."""
    health_fixes = plugin_manager_with_fix.get_health_fixes()

    assert "test-fix" in health_fixes
    assert health_fixes["test-fix"].summary == "A test health fix"


def test_health_fix_listed(health_fix_plugin, conda_cli):
    """Test that registered health fixes appear in --list output."""
    out, err, code = conda_cli("fix", "--list")

    assert "test-fix" in out
    assert "A test health fix" in out
    assert not code


def test_health_fix_executed(health_fix_plugin, conda_cli):
    """Test that health fixes are executed when invoked."""
    out, err, code = conda_cli("fix", "test-fix")

    assert health_fix_plugin.execute_called
    assert not code


def test_health_fix_receives_args(health_fix_plugin, conda_cli):
    """Test that health fixes receive parsed arguments."""
    conda_cli("fix", "test-fix", "--test-option")

    assert health_fix_plugin.execute_called
    assert health_fix_plugin.execute_args.test_option is True


def test_health_fix_receives_dry_run(health_fix_plugin, conda_cli):
    """Test that health fixes receive --dry-run flag."""
    conda_cli("fix", "test-fix", "--dry-run")

    assert health_fix_plugin.execute_called
    assert health_fix_plugin.execute_args.dry_run is True


def test_health_fix_receives_yes(health_fix_plugin, conda_cli):
    """Test that health fixes receive --yes flag."""
    conda_cli("fix", "test-fix", "--yes")

    assert health_fix_plugin.execute_called
    assert health_fix_plugin.execute_args.yes is True


def test_health_fix_not_executed_on_other_commands(health_fix_plugin, conda_cli):
    """Test that health fixes are not executed on unrelated commands."""
    conda_cli("info")

    assert not health_fix_plugin.execute_called
