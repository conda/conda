# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from typing import TYPE_CHECKING
from unittest import mock

import pytest

from conda import plugins
from conda.core.path_actions import _Action

# Attempt to load libmamba solver plugin since it's much faster;
# fall back if it's not available
try:
    from conda_libmamba_solver import plugin as solver_plugin

    env_flags: tuple = tuple()
except:
    solver_plugin = plugins.solvers
    env_flags = ("--solver=classic",)

if TYPE_CHECKING:
    from collections.abc import Iterable


class DummyActionPlugin:
    def dummy_hook(self, action: _Action) -> None:
        pass

    @plugins.hookimpl
    def conda_post_transactions(self) -> Iterable[plugins.CondaPostTransaction]:
        yield plugins.CondaPostTransaction(
            name="foo",
            run=self.dummy_hook,
        )


@pytest.fixture()
def post_transaction_plugin(plugin_manager_with_reporter_backends):
    # Explicitly load the solver, since this is a dummy plugin manager and not the default
    plugin_manager_with_reporter_backends.load_plugins(solver_plugin)

    plugin = DummyActionPlugin()
    with mock.patch.object(
        plugin, "dummy_hook", wraps=plugin.dummy_hook
    ) as mock_dummy_hook:
        plugin_manager_with_reporter_backends.register(plugin)

        yield mock_dummy_hook


def test_post_transaction_invoked(tmp_env, post_transaction_plugin):
    """Test that the post transaction hooks get invoked."""
    with tmp_env("python=3", *env_flags):
        pass

    post_transaction_plugin.assert_called()
    assert isinstance(post_transaction_plugin.call_args_list[0].args[0], _Action)


def test_post_transaction_raises_exception(tmp_env, post_transaction_plugin):
    """Test that exceptions get bubbled up from inside the post-transaction hooks."""
    msg = "💥"
    post_transaction_plugin.side_effect = Exception(msg)

    with pytest.raises(Exception, match=msg):
        with tmp_env("python=3", *env_flags):
            pass

    post_transaction_plugin.assert_called()
    assert isinstance(post_transaction_plugin.call_args_list[0].args[0], _Action)
