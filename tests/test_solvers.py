# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from typing import TYPE_CHECKING

from conda.testing.solver_helpers import SolverTests

if TYPE_CHECKING:
    from conda.core.solve import Solver


class TestClassicSolver(SolverTests):
    @property
    def solver_class(self) -> type[Solver]:
        from conda.plugins.solvers.classic.solver import ClassicSolver

        return ClassicSolver


class TestLibMambaSolver(SolverTests):
    @property
    def solver_class(self) -> type[Solver]:
        from conda_libmamba_solver.solver import LibMambaSolver

        return LibMambaSolver

    @property
    def tests_to_skip(self):
        return {
            "conda-libmamba-solver does not support features": [
                "test_iopro_mkl",
                "test_iopro_nomkl",
                "test_mkl",
                "test_accelerate",
                "test_scipy_mkl",
                "test_pseudo_boolean",
                "test_no_features",
                "test_surplus_features_1",
                "test_surplus_features_2",
                "test_remove",
                # this one below only fails reliably on windows;
                # it passes Linux on CI, but not locally?
                "test_unintentional_feature_downgrade",
            ],
        }
