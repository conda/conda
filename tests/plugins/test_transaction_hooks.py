# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from conda import plugins
from conda.core.path_actions import Action
from conda.plugins import package_extractors, solvers
from conda.plugins.types import CondaPostTransactionAction, CondaPreTransactionAction

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path


class DummyTransactionAction(Action):
    def verify(self):
        pass

    def execute(self):
        pass

    def reverse(self):
        pass

    def cleanup(self):
        pass


class DummyPostTransactionAction(DummyTransactionAction):
    pass


class DummyPreTransactionAction(DummyTransactionAction):
    pass


class DummyPreActionPlugin:
    @plugins.hookimpl
    def conda_pre_transaction_actions(self) -> Iterable[CondaPreTransactionAction]:
        yield CondaPreTransactionAction(
            name="bar",
            action=DummyPreTransactionAction,
        )


class DummyPostActionPlugin:
    @plugins.hookimpl
    def conda_post_transaction_actions(self) -> Iterable[CondaPostTransactionAction]:
        yield CondaPostTransactionAction(
            name="foo",
            action=DummyPostTransactionAction,
        )


@pytest.fixture
def plugin_manager_with_solvers(plugin_manager_with_reporter_backends, mocker):
    # Explicitly load the solver, since this is a dummy plugin manager and not the default
    plugin_manager_with_reporter_backends.load_plugins(
        solvers,
        *package_extractors.plugins,
    )

    return plugin_manager_with_reporter_backends


@pytest.fixture
def pre_transaction_plugin(plugin_manager_with_solvers, mocker):
    pre_plugin = DummyPreActionPlugin()
    mock_pre_verify = mocker.spy(DummyPreTransactionAction, "verify")
    mock_pre_execute = mocker.spy(DummyPreTransactionAction, "execute")
    mock_pre_reverse = mocker.spy(DummyPreTransactionAction, "reverse")
    mock_pre_cleanup = mocker.spy(DummyPreTransactionAction, "cleanup")

    plugin_manager_with_solvers.register(pre_plugin)

    return (mock_pre_verify, mock_pre_execute, mock_pre_reverse, mock_pre_cleanup)


@pytest.fixture
def post_transaction_plugin(plugin_manager_with_solvers, mocker):
    post_plugin = DummyPostActionPlugin()
    mock_post_verify = mocker.spy(DummyPostTransactionAction, "verify")
    mock_post_execute = mocker.spy(DummyPostTransactionAction, "execute")
    mock_post_reverse = mocker.spy(DummyPostTransactionAction, "reverse")
    mock_post_cleanup = mocker.spy(DummyPostTransactionAction, "cleanup")

    plugin_manager_with_solvers.register(post_plugin)

    return (mock_post_verify, mock_post_execute, mock_post_reverse, mock_post_cleanup)


def test_transaction_hooks_invoked(
    tmp_env,
    pre_transaction_plugin,
    post_transaction_plugin,
    test_recipes_channel: Path,
):
    """Test that the transaction hooks are invoked as expected."""
    pre_verify, pre_execute, pre_reverse, pre_cleanup = pre_transaction_plugin
    post_verify, post_execute, post_reverse, post_cleanup = post_transaction_plugin

    with tmp_env("small-executable", "--solver=classic"):
        pass

    pre_verify.assert_called_once()
    pre_execute.assert_called_once()
    pre_reverse.assert_not_called()
    pre_cleanup.assert_called_once()

    post_verify.assert_called_once()
    post_execute.assert_called_once()
    post_reverse.assert_not_called()
    post_cleanup.assert_called_once()


def test_pre_transaction_raises_exception(
    tmp_env,
    pre_transaction_plugin,
    test_recipes_channel: Path,
):
    """Test that exceptions get bubbled up from inside the pre-transaction hooks."""
    msg = "💥"

    pre_verify, pre_execute, pre_reverse, pre_cleanup = pre_transaction_plugin
    pre_execute.side_effect = Exception(msg)

    with pytest.raises(Exception, match=msg):
        with tmp_env("small-executable", "--solver=classic"):
            pass

    pre_verify.assert_called_once()
    pre_execute.assert_called_once()

    # Should this be assert_called_once()?
    # UnlinkLinkTransaction appears to double-rollback on error
    pre_reverse.assert_called()

    pre_cleanup.assert_not_called()


def test_post_transaction_raises_exception(
    tmp_env,
    post_transaction_plugin,
    test_recipes_channel: Path,
):
    """Test that exceptions get bubbled up from inside the post-transaction hooks."""
    msg = "💥"

    post_verify, post_execute, post_reverse, post_cleanup = post_transaction_plugin
    post_execute.side_effect = Exception(msg)

    with pytest.raises(Exception, match=msg):
        with tmp_env("small-executable", "--solver=classic"):
            pass

    post_verify.assert_called_once()
    post_execute.assert_called_once()

    # Should this be assert_called_once()?
    # UnlinkLinkTransaction appears to double-rollback on error
    post_reverse.assert_called()

    post_cleanup.assert_not_called()
