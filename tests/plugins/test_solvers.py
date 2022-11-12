# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import logging
import re

import pytest

from conda.core import solve
from conda.base.context import context
from conda.exceptions import PluginError
from conda import plugins


log = logging.getLogger(__name__)


class VerboseSolver(solve.Solver):
    def solve_final_state(self, *args, **kwargs):
        log.info("My verbose solver!")
        return super().solve_final_state(*args, **kwargs)


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
    assert plugin_manager.get_registered_plugins("solvers") == []


def test_get_one_solver(plugin_manager):
    plugin_manager.register(SolverPlugin())
    solvers = plugin_manager.get_registered_plugins("solvers")
    assert solvers == [classic_solver]


def test_get_two_solvers(plugin_manager):
    plugin_manager.register(SolverPlugin())

    verbose_classic_solver = plugins.CondaSolver(
        name="verbose-classic",
        backend=VerboseSolver,
    )

    plugin2 = VerboseSolverPlugin()
    plugin_manager.register(plugin2)

    solvers = plugin_manager.get_registered_plugins("solvers")
    assert solvers == [classic_solver, verbose_classic_solver]


def test_get_conflicting_solvers(plugin_manager):
    plugin_manager.register(SolverPlugin())
    plugin_manager.register(SolverPlugin())

    with pytest.raises(
        PluginError, match=re.escape("Conflicting `solvers` plugins found")
    ):
        plugin_manager.get_registered_plugins("solvers")
