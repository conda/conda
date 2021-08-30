# SPDX-License-Identifier: BSD-3-Clause

import contextlib
import tempfile

from typing import Type

import conda.core.solve

from conda.base.context import context
from conda.models.channel import Channel
from conda.resolve import MatchSpec

from . import helpers


class SolverTests:
    """Tests for :py:class:`conda.core.solve.Solver` implementations."""

    @property
    def solver(self) -> Type[conda.core.solve.Solver]:
        raise NotImplementedError

    @contextlib.contextmanager
    def simple_solver(self, *, add=(), remove=()):
        with tempfile.TemporaryDirectory(prefix='conda-solver-test-') as tmpdir:
            helpers.get_index_r_1(context.subdir)
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

    def assert_installed(self, specs, expecting):
        assert sorted(
            record.dist_str() for record in self.install(*specs)
         ) == sorted(helpers.add_subdir_to_iter(expecting))

    def test_empty(self):
        assert self.install() == []

    def test_iopro_nomkl(self):
        self.assert_installed(
            ['iopro 1.4*', 'python 2.7*', 'numpy 1.7*'], [
                'channel-1::iopro-1.4.3-np17py27_p0',
                'channel-1::numpy-1.7.1-py27_0',
                'channel-1::openssl-1.0.1c-0',
                'channel-1::python-2.7.5-0',
                'channel-1::readline-6.2-0',
                'channel-1::sqlite-3.7.13-0',
                'channel-1::system-5.8-1',
                'channel-1::tk-8.5.13-0',
                'channel-1::unixodbc-2.3.1-0',
                'channel-1::zlib-1.2.7-0',
            ],
        )

    def test_mkl(self):
        assert self.install('mkl') == self.install(
            'mkl 11*', MatchSpec(track_features='mkl')
        )


class TestLegacySolver(SolverTests):
    @property
    def solver(self):
        return conda.core.solve.Solver


class TestLibSolvSolver(SolverTests):
    @property
    def solver(self):
        return conda.core.solve.LibSolvSolver
