# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import pytest
from pytest_mock import MockerFixture

from conda import plugins
from conda.exceptions import DryRunExit
from conda.plugins import solvers
from conda.plugins.manager import CondaPluginManager
from conda.testing import CondaCLIFixture, PathFactoryFixture


class PostSolvePlugin:
    def post_solve_action(self) -> None:
        pass

    @plugins.hookimpl
    def conda_post_solves(self):
        yield plugins.CondaPostSolve(
            name="custom-post-solve",
            action=self.post_solve_action,
        )


@pytest.fixture
def post_solve_plugin(
    mocker: MockerFixture, plugin_manager: CondaPluginManager
) -> PostSolvePlugin:
    mocker.patch.object(PostSolvePlugin, "post_solve_action")

    post_solve_plugin = PostSolvePlugin()
    plugin_manager.register(post_solve_plugin)

    # register solvers
    plugin_manager.load_plugins(solvers)

    return post_solve_plugin


def test_post_solve_invoked(
    post_solve_plugin: PostSolvePlugin,
    conda_cli: CondaCLIFixture,
    path_factory: PathFactoryFixture,
):
    with pytest.raises(DryRunExit):
        conda_cli("install", "zlib", "--dry-run")

    assert len(post_solve_plugin.post_solve_action.mock_calls) == 1


def test_post_solve_not_invoked(
    post_solve_plugin: PostSolvePlugin, conda_cli: CondaCLIFixture
):
    conda_cli("config")

    assert len(post_solve_plugin.post_solve_action.mock_calls) == 0


def test_post_solve_action_raises_exception(
    post_solve_plugin: PostSolvePlugin,
    conda_cli: CondaCLIFixture,
    path_factory: PathFactoryFixture,
):
    exc_message = "💥"
    post_solve_plugin.post_solve_action.side_effect = [Exception(exc_message)]

    with pytest.raises(Exception, match=exc_message):
        conda_cli("install", "zlib", "--dry-run")

    assert len(post_solve_plugin.post_solve_action.mock_calls) == 1
