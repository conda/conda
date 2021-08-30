# SPDX-License-Identifier: BSD-3-Clause

import contextlib
import tempfile

from typing import Type

import conda.core.solve

from conda.base.context import context
from conda.models.channel import Channel


class SolverTests:
    """Tests for :py:class:`conda.core.solve.Solver` implementations."""

    @property
    def solver(self) -> Type[conda.core.solve.Solver]:
        raise NotImplementedError

    @contextlib.contextmanager
    def simple_solver(self, *, add=(), remove=()):
        with tempfile.TemporaryDirectory(prefix='conda-solver-test-') as tmpdir:
            yield self.solver(
                prefix=tmpdir,
                subdirs=(context.subdir,),
                channels=(Channel('channel-1'),),
                specs_to_add=add,
                specs_to_remove=remove,
            )

    def install(self, *specs):
        with self.simple_solver(add=specs) as solver:
            return solver.solve_final_state()

    def test_empty(self):
        assert self.install() == []


class TestLegacySolver(SolverTests):
    @property
    def solver(self):
        return conda.core.solve.Solver


class TestLibSolvSolver(SolverTests):
    @property
    def solver(self):
        return conda.core.solve.LibSolvSolver
