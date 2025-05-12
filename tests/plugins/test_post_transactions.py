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


class DummyActionPlugin:
    @plugins.hookimpl
    def conda_post_transactions(self) -> Iterable[plugins.CondaPostTransaction]:
        yield plugins.CondaPostTransaction(
            name="foo",
            action=DummyTransactionAction,
        )


@pytest.fixture()
def post_transaction_plugin(plugin_manager_with_reporter_backends, mocker):
    """Test that post transaction actions get called."""
    # Explicitly load the solver, since this is a dummy plugin manager and not the default
    plugin_manager_with_reporter_backends.load_plugins(plugins.solvers)

    plugin = DummyActionPlugin()
    mock_verify = mocker.spy(DummyTransactionAction, "verify")
    mock_execute = mocker.spy(DummyTransactionAction, "execute")
    mock_reverse = mocker.spy(DummyTransactionAction, "reverse")
    mock_cleanup = mocker.spy(DummyTransactionAction, "cleanup")

    plugin_manager_with_reporter_backends.register(plugin)

    return mock_verify, mock_execute, mock_reverse, mock_cleanup


def test_post_transaction_invoked(tmp_env, post_transaction_plugin, caplog):
    with caplog.at_level(logging.INFO):
        with tmp_env("python=3", "--solver=classic"):
            pass

    mock_verify, mock_execute, mock_reverse, mock_cleanup = post_transaction_plugin
    mock_verify.assert_called_once()
    mock_execute.assert_called_once()
    mock_reverse.assert_not_called()
    mock_cleanup.assert_called_once()


def test_post_transaction_raises_exception(tmp_env, post_transaction_plugin):
    """Test that exceptions get bubbled up from inside the post-transaction hooks."""
    msg = "💥"
    mock_verify, mock_execute, mock_reverse, mock_cleanup = post_transaction_plugin
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
