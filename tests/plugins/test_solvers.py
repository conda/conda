# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import logging
import re

import pytest

from conda.core import solve
from conda.exceptions import PluginError
from conda.models.plugins import CondaSolver
from conda import plugins
from conda.plugins.solvers import get_available_solvers


log = logging.getLogger(__name__)


class Solver(solve.Solver):
    pass


class VerboseSolver(solve.Solver):
    def solve_final_state(self, *args, **kwargs):
        log.info("My verbose solver!")
        return super().solve_final_state(*args, **kwargs)


classic_solver = CondaSolver(
    name="classic",
    backend=Solver,
)


class SolverPlugin:
    @plugins.hookimpl
    def conda_solvers(self):
        yield classic_solver


class VerboseSolverPlugin:
    @plugins.hookimpl
    def conda_solvers(self):
        yield CondaSolver(
            name="verbose-classic",
            backend=VerboseSolver,
        )


@pytest.fixture()
def plugin(plugin_manager):
    plugin = SolverPlugin()
    plugin_manager.register(plugin)
    return plugin


def test_get_solver_class(plugin):
    solver_class = solve._get_solver_class()
    assert solver_class is Solver


def test_get_solver_class_multiple(plugin_manager):
    plugin = SolverPlugin()
    plugin_manager.register(plugin)

    plugin2 = VerboseSolverPlugin()
    plugin_manager.register(plugin2)

    solver_class = solve._get_solver_class()
    assert solver_class is Solver
    solver_class = solve._get_solver_class("verbose-classic")
    assert solver_class is VerboseSolver


def test_duplicated(plugin_manager):
    plugin_manager.register(SolverPlugin())
    plugin_manager.register(SolverPlugin())

    with pytest.raises(
        PluginError, match=re.escape("Conflicting entries found for the following solvers")
    ):
        solve._get_solver_class()


def test_none_get_available_solvers(plugin_manager):
    assert get_available_solvers(plugin_manager) == []


def test_one_get_available_solvers(plugin_manager):
    plugin_manager.register(SolverPlugin())
    solvers = get_available_solvers(plugin_manager)
    assert solvers == [classic_solver]


def test_two_get_available_solvers(plugin_manager):
    plugin_manager.register(SolverPlugin())

    verbose_classic_solver = CondaSolver(
        name="verbose-classic",
        backend=VerboseSolver,
    )

    plugin2 = VerboseSolverPlugin()
    plugin_manager.register(plugin2)

    solvers = get_available_solvers(plugin_manager)
    assert solvers == [classic_solver, verbose_classic_solver]


def test_conflicting_get_available_solvers(plugin_manager):
    plugin_manager.register(SolverPlugin())
    plugin_manager.register(SolverPlugin())

    with pytest.raises(
        PluginError, match=re.escape("Conflicting entries found for the following solvers")
    ):
        get_available_solvers(plugin_manager)
