# SPDX-FileCopyrightText: © 2012 Continuum Analytics, Inc. <http://continuum.io>
# SPDX-FileCopyrightText: © 2017 Anaconda, Inc. <https://www.anaconda.com>
# SPDX-License-Identifier: BSD-3-Clause
from conda.core.solve import Solver
from conda.testing.solver_helpers import SolverTests


class TestClassicSolver(SolverTests):
    @property
    def solver_class(self):
        return Solver
