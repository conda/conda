# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from conda.core.solve import Solver
from conda.testing.solver_helpers import SolverTests


class TestClassicSolver(SolverTests):
    @property
    def solver_class(self):
        return Solver
