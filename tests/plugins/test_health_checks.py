# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import pytest

from conda import plugins
from conda.plugins.types import CondaHealthChecks


class HealthCheckPlugin:
    def health_check_action(self):
        pass

    @plugins.hookimpl
    def conda_health_checks(self):
        yield CondaHealthChecks(
            name="test-health-check",
            action=self.health_check_action,
        )


@pytest.fixture()
def health_check_plugin(mocker, plugin_manager):
    mocker.patch.object(HealthCheckPlugin, "health_check_action")

    health_check_plugin = HealthCheckPlugin()
    plugin_manager.register(health_check_plugin)

    return health_check_plugin


def test_health_check_ran(health_check_plugin, conda_cli):
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
