# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import random
import signal
import time
from contextlib import contextmanager
from typing import TYPE_CHECKING
from unittest import mock

import pytest

from conda import plugins
from conda.core.path_actions import Action, CreatePrefixRecordAction

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator


@contextmanager
def limit_time(seconds: int) -> Iterator:
    """A context manager that raises a TimeoutError if execution takes too long.

    If this decorates a function that runs not on the main thread, or the platform
    is not Unix, this does nothing.

    :param seconds: Length of time the context has to run before an error is raised
    """

    def handler(signum, frame):
        raise TimeoutError

    has_sigalrm = True

    try:
        signal.signal(signal.SIGALRM, handler)
        signal.alarm(seconds)
    except (ValueError, AttributeError):
        # Not the main thread or SIGALRM is not implemented
        has_sigalrm = False

    try:
        yield
    finally:
        if has_sigalrm:
            signal.alarm(0)


class OverheadActionPlugin:
    def overhead_hook(self, action: Action) -> None:
        time.sleep(random.uniform(0.001, 0.1))

    @plugins.hookimpl
    def conda_post_transactions(self) -> Iterable[plugins.CondaPostTransaction]:
        yield plugins.CondaPostTransaction(
            name="add_overhead",
            run=self.overhead_hook,
            action_type=CreatePrefixRecordAction,
        )


class DummyActionPlugin:
    def dummy_hook(self, action: Action) -> None:
        pass

    @plugins.hookimpl
    def conda_post_transactions(self) -> Iterable[plugins.CondaPostTransaction]:
        yield plugins.CondaPostTransaction(
            name="foo",
            run=self.dummy_hook,
        )


@pytest.fixture()
def post_transaction_plugin_overhead(plugin_manager_with_reporter_backends):
    # Explicitly load the solver, since this is a dummy plugin manager and not the default
    plugin_manager_with_reporter_backends.load_plugins(plugins.solvers)

    plugin = OverheadActionPlugin()
    with mock.patch.object(
        plugin, "overhead_hook", wraps=plugin.overhead_hook
    ) as mock_hook:
        plugin_manager_with_reporter_backends.register(plugin)

        yield mock_hook


@pytest.fixture()
def post_transaction_plugin(plugin_manager_with_reporter_backends):
    # Explicitly load the solver, since this is a dummy plugin manager and not the default
    plugin_manager_with_reporter_backends.load_plugins(plugins.solvers)

    plugin = DummyActionPlugin()
    with mock.patch.object(
        plugin, "dummy_hook", wraps=plugin.dummy_hook
    ) as mock_dummy_hook:
        plugin_manager_with_reporter_backends.register(plugin)

        yield mock_dummy_hook


def test_post_transaction_invoked(tmp_env, post_transaction_plugin):
    """Test that the post transaction hooks get invoked."""
    with tmp_env("python=3", "--solver=classic"):
        pass

    post_transaction_plugin.assert_called()
    assert isinstance(post_transaction_plugin.call_args_list[0].args[0], Action)


def test_post_transaction_raises_exception(tmp_env, post_transaction_plugin):
    """Test that exceptions get bubbled up from inside the post-transaction hooks."""
    msg = "💥"
    post_transaction_plugin.side_effect = Exception(msg)

    with pytest.raises(Exception, match=msg):
        with tmp_env("python=3", "--solver=classic"):
            pass

    post_transaction_plugin.assert_called()
    assert isinstance(post_transaction_plugin.call_args_list[0].args[0], Action)


def test_post_transaction_overhead(tmp_env, post_transaction_plugin_overhead):
    """Test that the post transaction hooks don't cause too much overhead."""
    with limit_time(400):
        with tmp_env("python=3", "--solver=classic"):
            pass

        post_transaction_plugin_overhead.assert_called()
        assert isinstance(
            post_transaction_plugin_overhead.call_args_list[0].args[0],
            Action,
        )
