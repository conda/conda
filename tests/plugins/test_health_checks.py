# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import pytest

from conda import plugins
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
