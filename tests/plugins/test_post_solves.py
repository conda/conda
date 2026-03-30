# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from conda import plugins
from conda.exceptions import DryRunExit
from conda.plugins import solvers

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from conda.plugins.manager import CondaPluginManager
    from conda.testing.fixtures import (
        CondaCLIFixture,
        PathFactoryFixture,
        TmpEnvFixture,
    )


class PostSolvePlugin:
    def post_solve_action(self) -> None:
        pass

    @plugins.hookimpl
    def conda_post_solves(self):
        yield plugins.types.CondaPostSolve(
            name="custom-post-solve",
            action=self.post_solve_action,
        )


@pytest.fixture
def post_solve_plugin(
    mocker: MockerFixture,
    plugin_manager_with_reporter_backends: CondaPluginManager,
) -> PostSolvePlugin:
    mocker.patch.object(PostSolvePlugin, "post_solve_action")

    post_solve_plugin = PostSolvePlugin()
    plugin_manager_with_reporter_backends.register(post_solve_plugin)

    # register solvers
    plugin_manager_with_reporter_backends.load_plugins(solvers)

    return post_solve_plugin


def test_post_solve_invoked(
    post_solve_plugin: PostSolvePlugin,
    tmp_env: TmpEnvFixture,
    path_factory: PathFactoryFixture,
):
    with pytest.raises(DryRunExit):
        with tmp_env("zlib", "--solver=classic", "--dry-run"):
            pass

    assert post_solve_plugin.post_solve_action.mock_calls


def test_post_solve_not_invoked(
    post_solve_plugin: PostSolvePlugin,
    conda_cli: CondaCLIFixture,
):
    conda_cli("config")

    assert not post_solve_plugin.post_solve_action.mock_calls


def test_post_solve_action_raises_exception(
    post_solve_plugin: PostSolvePlugin,
    tmp_env: TmpEnvFixture,
    path_factory: PathFactoryFixture,
):
    exc_message = "💥"
    post_solve_plugin.post_solve_action.side_effect = [Exception(exc_message)]

    with pytest.raises(Exception, match=exc_message):
        with tmp_env("zlib", "--solver=classic", "--dry-run"):
            pass

    assert post_solve_plugin.post_solve_action.mock_calls
