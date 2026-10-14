# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import pytest

from conda import plugins
from conda.base.context import context
from conda.exceptions import CondaSystemExit
from conda.plugins.subcommands import doctor
from conda.plugins.types import CondaHealthCheck


class HealthCheckPlugin:
    def health_check_action(self):
        pass

    @plugins.hookimpl
    def conda_health_checks(self):
        yield CondaHealthCheck(
            name="test-health-check",
            action=self.health_check_action,
        )


@pytest.fixture()
def plugin_manager_with_doctor_command(plugin_manager_with_reporter_backends):
    """
    Registers the `conda doctor` subcommand
    """
    plugin_manager_with_reporter_backends.load_plugins(doctor)

    return plugin_manager_with_reporter_backends


@pytest.fixture()
def health_check_plugin(mocker, plugin_manager_with_doctor_command):
    mocker.patch.object(HealthCheckPlugin, "health_check_action")

    health_check_plugin = HealthCheckPlugin()
    plugin_manager_with_doctor_command.register(health_check_plugin)

    return health_check_plugin


def test_health_check_ran(mocker, health_check_plugin, conda_cli):
    """
    Test for the case when the health check successfully ran.
    """
    conda_cli("doctor")
    assert len(health_check_plugin.health_check_action.mock_calls) == 1


def test_health_check_not_ran(health_check_plugin, conda_cli):
    """
    Test for the case when the health check did not run.
    """

    conda_cli("info")
    assert len(health_check_plugin.health_check_action.mock_calls) == 0


class HealthCheckPluginWithFixer:
    """Health check plugin with a fixer that raises CondaSystemExit (user cancel)."""

    def health_check_action(self, prefix, verbose):
        pass

    def health_check_fixer(self, prefix, args, confirm):
        raise CondaSystemExit("Exiting.")

    @plugins.hookimpl
    def conda_health_checks(self):
        yield CondaHealthCheck(
            name="test-health-check-with-fixer",
            action=self.health_check_action,
            fixer=self.health_check_fixer,
        )


@pytest.fixture()
def health_check_plugin_with_fixer(mocker, plugin_manager_with_doctor_command):
    health_check_plugin = HealthCheckPluginWithFixer()
    plugin_manager_with_doctor_command.register(health_check_plugin)
    return health_check_plugin


def test_fix_user_cancels_no_warning(health_check_plugin_with_fixer, conda_cli, capsys):
    """
    Test that no warning is logged when user cancels a fix operation.

    When a user answers 'n' to a fix confirmation prompt, CondaSystemExit is raised.
    This should be caught silently without logging a warning message.
    """
    out, err, code = conda_cli("doctor", "--fix")

    # The user cancelled (via CondaSystemExit), so no warning should be shown
    assert "Error running fix" not in err
    # The warning would contain "Exiting" from CondaSystemExit
    assert "Exiting" not in err


class HealthCheckPluginWithContextAwareFixer:
    """Health check plugin with a fixer that records frozen-env protection."""

    def __init__(self):
        self.fixer_calls = []

    def health_check_action(self, prefix, verbose):
        pass

    def health_check_fixer(self, prefix, args, confirm):
        self.fixer_calls.append((args.protect_frozen_envs, context.protect_frozen_envs))
        return 0

    @plugins.hookimpl
    def conda_health_checks(self):
        yield CondaHealthCheck(
            name="test-context-aware-fixer",
            action=self.health_check_action,
            fixer=self.health_check_fixer,
        )


@pytest.fixture()
def health_check_plugin_with_context_aware_fixer(plugin_manager_with_doctor_command):
    health_check_plugin = HealthCheckPluginWithContextAwareFixer()
    plugin_manager_with_doctor_command.register(health_check_plugin)
    return health_check_plugin


def test_fix_override_frozen_reaches_plugin_fixer(
    health_check_plugin_with_context_aware_fixer,
    conda_cli,
):
    out, err, code = conda_cli("doctor", "--fix", "--yes", "--override-frozen")

    assert "Running fixes" in out
    assert not err
    assert code == 0
    assert health_check_plugin_with_context_aware_fixer.fixer_calls == [(False, False)]
