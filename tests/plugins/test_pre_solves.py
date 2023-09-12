# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import pytest
from pytest_mock import MockerFixture

from conda import plugins
from conda.exceptions import DryRunExit
from conda.plugins import solvers
from conda.plugins.manager import CondaPluginManager
from conda.testing import CondaCLIFixture, PathFactoryFixture


class PreSolvePlugin:
    def pre_solve_action(self) -> None:
        pass

    @plugins.hookimpl
    def conda_pre_solves(self):
        yield plugins.CondaPreSolve(
            name="custom-pre-solve",
            action=self.pre_solve_action,
        )


@pytest.fixture
def pre_solve_plugin(
    mocker: MockerFixture, plugin_manager: CondaPluginManager
) -> PreSolvePlugin:
    mocker.patch.object(PreSolvePlugin, "pre_solve_action")

    pre_solve_plugin = PreSolvePlugin()
    plugin_manager.register(pre_solve_plugin)

    # register solvers
    plugin_manager.load_plugins(solvers)

    return pre_solve_plugin


def test_pre_solve_invoked(
    pre_solve_plugin: PreSolvePlugin,
    conda_cli: CondaCLIFixture,
    path_factory: PathFactoryFixture,
):
    with pytest.raises(DryRunExit):
        conda_cli("install", "zlib", "--dry-run")

    assert len(pre_solve_plugin.pre_solve_action.mock_calls) == 1


def test_pre_solve_not_invoked(
    pre_solve_plugin: PreSolvePlugin, conda_cli: CondaCLIFixture
):
    conda_cli("config")

    assert len(pre_solve_plugin.pre_solve_action.mock_calls) == 0


def test_pre_solve_action_raises_exception(
    pre_solve_plugin: PreSolvePlugin,
    conda_cli: CondaCLIFixture,
    path_factory: PathFactoryFixture,
):
    exc_message = "💥"
    pre_solve_plugin.pre_solve_action.side_effect = [Exception(exc_message)]

    with pytest.raises(Exception, match=exc_message):
        conda_cli("install", "zlib", "--dry-run")

    assert len(pre_solve_plugin.pre_solve_action.mock_calls) == 1
