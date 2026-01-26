# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pytest

from conda import plugins
from conda.core.path_actions import Action

if TYPE_CHECKING:
    from collections.abc import Iterable


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
    def conda_pre_transaction_actions(
        self,
    ) -> Iterable[plugins.types.CondaPreTransactionAction]:
        yield plugins.types.CondaPreTransactionAction(
            name="bar",
            action=DummyPreTransactionAction,
        )


class DummyPostActionPlugin:
    @plugins.hookimpl
    def conda_post_transaction_actions(
        self,
    ) -> Iterable[plugins.types.CondaPostTransactionAction]:
        yield plugins.types.CondaPostTransactionAction(
            name="foo",
            action=DummyPostTransactionAction,
        )


@pytest.fixture()
def transaction_plugin(plugin_manager_with_reporter_backends, mocker):
    """Test that post transaction actions get called."""
    # Explicitly load the solver, since this is a dummy plugin manager and not the default
    plugin_manager_with_reporter_backends.load_plugins(plugins.solvers)
    plugin_manager_with_reporter_backends.load_plugins(
        *plugins.package_extractors.plugins
    )

    pre_plugin = DummyPreActionPlugin()
    mock_pre_verify = mocker.spy(DummyPreTransactionAction, "verify")
    mock_pre_execute = mocker.spy(DummyPreTransactionAction, "execute")
    mock_pre_reverse = mocker.spy(DummyPreTransactionAction, "reverse")
    mock_pre_cleanup = mocker.spy(DummyPreTransactionAction, "cleanup")

    post_plugin = DummyPostActionPlugin()
    mock_post_verify = mocker.spy(DummyPostTransactionAction, "verify")
    mock_post_execute = mocker.spy(DummyPostTransactionAction, "execute")
    mock_post_reverse = mocker.spy(DummyPostTransactionAction, "reverse")
    mock_post_cleanup = mocker.spy(DummyPostTransactionAction, "cleanup")

    plugin_manager_with_reporter_backends.register(pre_plugin)
    plugin_manager_with_reporter_backends.register(post_plugin)

    return (
        (mock_pre_verify, mock_pre_execute, mock_pre_reverse, mock_pre_cleanup),
        (mock_post_verify, mock_post_execute, mock_post_reverse, mock_post_cleanup),
    )


def test_transaction_hooks_invoked(tmp_env, transaction_plugin, caplog):
    """Test that the transaction hooks are invoked as expected."""
    with caplog.at_level(logging.INFO):
        with tmp_env("python=3", "--solver=classic"):
            pass

    mock_pre, mock_post = transaction_plugin

    mock_pre_verify, mock_pre_execute, mock_pre_reverse, mock_pre_cleanup = mock_pre
    mock_post_verify, mock_post_execute, mock_post_reverse, mock_post_cleanup = (
        mock_post
    )

    mock_pre_verify.assert_called_once()
    mock_pre_execute.assert_called_once()
    mock_pre_reverse.assert_not_called()
    mock_pre_cleanup.assert_called_once()

    mock_post_verify.assert_called_once()
    mock_post_execute.assert_called_once()
    mock_post_reverse.assert_not_called()
    mock_post_cleanup.assert_called_once()


def test_pre_transaction_raises_exception(tmp_env, transaction_plugin):
    """Test that exceptions get bubbled up from inside the pre-transaction hooks."""
    msg = "💥"

    mock_pre, _ = transaction_plugin
    mock_verify, mock_execute, mock_reverse, mock_cleanup = mock_pre
    mock_execute.side_effect = Exception(msg)

    with pytest.raises(Exception, match=msg):
        with tmp_env("python=3", "--solver=classic"):
            pass

    mock_verify.assert_called_once()
    mock_execute.assert_called_once()

    # Should this be assert_called_once()?
    # UnlinkLinkTransaction appears to double-rollback on error
    mock_reverse.assert_called()

    mock_cleanup.assert_not_called()


def test_post_transaction_raises_exception(tmp_env, transaction_plugin):
    """Test that exceptions get bubbled up from inside the post-transaction hooks."""
    msg = "💥"

    _, mock_post = transaction_plugin
    mock_verify, mock_execute, mock_reverse, mock_cleanup = mock_post
    mock_execute.side_effect = Exception(msg)

    with pytest.raises(Exception, match=msg):
        with tmp_env("python=3", "--solver=classic"):
            pass

    mock_verify.assert_called_once()
    mock_execute.assert_called_once()

    # Should this be assert_called_once()?
    # UnlinkLinkTransaction appears to double-rollback on error
    mock_reverse.assert_called()

    mock_cleanup.assert_not_called()
