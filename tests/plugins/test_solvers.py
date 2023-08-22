# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import logging
import re

import pytest

from conda import plugins
from conda.base.context import context
from conda.core import solve
from conda.exceptions import PluginError
from conda.plugins.hookspec import CondaSpecs
from conda.plugins.manager import CondaPluginManager

log = logging.getLogger(__name__)


verbose_user_agent = "verbose-solver/1.0"


class VerboseSolver(solve.Solver):
    def solve_final_state(self, *args, **kwargs):
        log.info("My verbose solver!")
        return super().solve_final_state(*args, **kwargs)

    @staticmethod
    def user_agent():
        return verbose_user_agent


classic_solver = plugins.CondaSolver(
    name="classic",
    backend=solve.Solver,
)


class SolverPlugin:
    @plugins.hookimpl
    def conda_solvers(self):
        yield classic_solver


class VerboseSolverPlugin:
    @plugins.hookimpl
    def conda_solvers(self):
        yield plugins.CondaSolver(
            name="verbose-classic",
            backend=VerboseSolver,
        )


def test_get_solver_backend(plugin_manager):
    plugin = SolverPlugin()
    plugin_manager.register(plugin)
    solver_class = plugin_manager.get_solver_backend()
    assert solver_class is solve.Solver


def test_get_cached_solver_backend(plugin_manager, mocker):
    mocked = mocker.patch(
        "conda.plugins.manager.CondaPluginManager.get_solver_backend",
        side_effect=classic_solver,
    )
    plugin_manager = CondaPluginManager()
    plugin_manager.add_hookspecs(CondaSpecs)
    plugin = SolverPlugin()
    plugin_manager.register(plugin)
    plugin_manager.get_cached_solver_backend()
    plugin_manager.get_cached_solver_backend()
    assert mocked.call_count == 1  # real caching!


def clear_user_agent():
    if "__user_agent" in context._cache_:
        del context._cache_["__user_agent"]


def test_solver_user_agent(monkeypatch, plugin_manager, request):
    # setting the solver to the verbose classic version defined in this module
    monkeypatch.setattr(context, "solver", "verbose-classic")
    # context.user_agent is a memoizedproperty, which may have been cached from
    # previous test runs. We're checking here and clear the cache if needed.
    request.addfinalizer(clear_user_agent)
    clear_user_agent()

    plugin = VerboseSolverPlugin()
    plugin_manager.register(plugin)
    assert verbose_user_agent in context.user_agent


def test_get_solver_backend_multiple(plugin_manager):
    plugin = SolverPlugin()
    plugin_manager.register(plugin)

    plugin2 = VerboseSolverPlugin()
    plugin_manager.register(plugin2)

    solver_class = plugin_manager.get_solver_backend()
    assert solver_class is solve.Solver
    solver_class = plugin_manager.get_solver_backend("verbose-classic")
    assert solver_class is VerboseSolver


def test_duplicated(plugin_manager):
    plugin_manager.register(SolverPlugin())
    plugin_manager.register(SolverPlugin())

    with pytest.raises(
        PluginError, match=re.escape("Conflicting `solvers` plugins found")
    ):
        plugin_manager.get_solver_backend()


def test_get_no_solver(plugin_manager):
    assert plugin_manager.get_hook_results("solvers") == []


def test_get_one_solver(plugin_manager):
    plugin_manager.register(SolverPlugin())
    solvers = plugin_manager.get_hook_results("solvers")
    assert solvers == [classic_solver]


def test_get_two_solvers(plugin_manager):
    plugin_manager.register(SolverPlugin())

    verbose_classic_solver = plugins.CondaSolver(
        name="verbose-classic",
        backend=VerboseSolver,
    )

    plugin2 = VerboseSolverPlugin()
    plugin_manager.register(plugin2)

    solvers = plugin_manager.get_hook_results("solvers")
    assert solvers == [classic_solver, verbose_classic_solver]


def test_get_conflicting_solvers(plugin_manager):
    plugin_manager.register(SolverPlugin())
    plugin_manager.register(SolverPlugin())

    with pytest.raises(
        PluginError, match=re.escape("Conflicting `solvers` plugins found")
    ):
        plugin_manager.get_hook_results("solvers")
