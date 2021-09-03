# SPDX-License-Identifier: BSD-3-Clause

import contextlib
import re
import tempfile
import textwrap

from typing import Type

import pytest

import conda.core.solve

from conda.base.context import context
from conda.exceptions import ResolvePackageNotFound, UnsatisfiableError
from conda.models.channel import Channel
from conda.resolve import MatchSpec

from . import helpers


class SolverTests:
    """Tests for :py:class:`conda.core.solve.Solver` implementations."""

    @property
    def solver_class(self) -> Type[conda.core.solve.Solver]:
        raise NotImplementedError

    @contextlib.contextmanager
    def _cache_channel_packages(self, channel, packages):
        # instantiating the data should cache it
        sd = helpers.TestSubdirData(channel, packages=list(packages))
        key = (channel.url(with_credentials=True), REPODATA_FN)
        assert key in SubdirData._cache_
        try:
            yield
        finally:
            del SubdirData._cache_[key]

    @contextlib.contextmanager
    def solver(self, *, add=(), remove=(), packages=()):
        channel = Channel('https://conda.anaconda.org/channel-custom/%s' % context.subdir)
        with contextlib.ExitStack() as stack:
            # cache the packages for all subdirs as the resolver might want to access them
            for subdir in context.subdirs:
                stack.enter_context(self._cache_channel_packages(
                    Channel('https://conda.anaconda.org/channel-custom/%s' % subdir),
                    list(packages),
                ))
            # yield the solver
            yield self.solver_class(
                prefix='dummy - does not exist',
                subdirs=(context.subdir,),
                channels=(channel,),
                specs_to_add=add,
                specs_to_remove=remove,
            )

    def install(self, *specs, packages=None):
        if not packages:
            packages = self.index(1)
        with self.solver(add=specs, packages=packages) as solver:
            return solver.solve_final_state()

    def index(self, num):
        # XXX: get_index_r_X should probably be refactored to avoid loading the environment like this.
        get_index = getattr(helpers, f'get_index_r_{num}')
        index, _ = get_index(context.subdir)
        return index.values()

    def assert_installed(self, specs, expecting):
        assert sorted(
            record.dist_str() for record in self.install(*specs)
         ) == sorted(helpers.add_subdir_to_iter(expecting))

    def assert_record_in(self, record_str, records):
        assert helpers.add_subdir(record_str) in [
            record.dist_str() for record in records
        ]

    def assert_unsatisfiable(self, exc_info, entries):
        assert exc_info.type is UnsatisfiableError
        assert sorted(
            tuple(map(str, entries))
            for entries in exc_info.value.unsatisfiable
        ) == entries

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

    def test_accelerate(self):
        assert self.install('accelerate') == self.install(
            'accelerate', MatchSpec(track_features='mkl')
        )

    def test_scipy_mkl(self):
        records = self.install('scipy', 'python 2.7*', 'numpy 1.7*', MatchSpec(track_features='mkl'))

        for record in records:
            if record.name in ('numpy', 'scipy'):
                assert 'mkl' in record.features

        self.assert_record_in('channel-1::numpy-1.7.1-py27_p0', records)
        self.assert_record_in('channel-1::scipy-0.12.0-np17py27_p0', records)

    def test_anaconda_nomkl(self):
        records = self.install('anaconda 1.5.0', 'python 2.7*', 'numpy 1.7*')
        assert len(records) == 107
        self.assert_record_in('channel-1::scipy-0.12.0-np17py27_0', records)

    def test_pseudo_boolean(self):
        # The latest version of iopro, 1.5.0, was not built against numpy 1.5
        self.assert_installed(
            ['iopro', 'python 2.7*', 'numpy 1.5*'], [
                'channel-1::iopro-1.4.3-np15py27_p0',
                'channel-1::numpy-1.5.1-py27_4',
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
        self.assert_installed(
            ['iopro', 'python 2.7*', 'numpy 1.5*', MatchSpec(track_features='mkl')], [
                'channel-1::iopro-1.4.3-np15py27_p0',
                'channel-1::mkl-rt-11.0-p0',
                'channel-1::numpy-1.5.1-py27_p4',
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

    def test_unsat_from_r1(self):
        with pytest.raises(UnsatisfiableError) as exc_info:
            self.install('numpy 1.5*', 'scipy 0.12.0b1')
        self.assert_unsatisfiable(exc_info, [
            ('numpy=1.5',),
            ('scipy==0.12.0b1', "numpy[version='1.6.*|1.7.*']"),
        ])

        with pytest.raises(UnsatisfiableError) as exc_info:
            self.install('numpy 1.5*', 'python 3*')
        self.assert_unsatisfiable(exc_info, [
            ('numpy=1.5', 'nose', 'python=3.3'),
            ('numpy=1.5', "python[version='2.6.*|2.7.*']"),
            ('python=3',),
        ])

        with pytest.raises(ResolvePackageNotFound) as exc_info:
            self.install('numpy 1.5*', 'numpy 1.6*')
        assert sorted(map(str, exc_info.value.bad_deps)) == [
            "numpy[version='1.5.*,1.6.*']",
        ]

    def test_unsat_simple(self):
        with pytest.raises(UnsatisfiableError) as exc_info:
            self.install(
                'a', 'b',
                packages=(
                    helpers.SimpleRecord(name='a', depends=['c >=1,<2']),
                    helpers.SimpleRecord(name='b', depends=['c >=2,<3']),
                    helpers.SimpleRecord(name='c', version='1.0'),
                    helpers.SimpleRecord(name='c', version='2.0'),
                )
            )
        self.assert_unsatisfiable(exc_info, [
            ('a', "c[version='>=1,<2']"),
            ('b', "c[version='>=2,<3']"),
        ])


class TestLegacySolver(SolverTests):
    @property
    def solver_class(self):
        return conda.core.solve.Solver


class TestLibSolvSolver(SolverTests):
    @property
    def solver_class(self):
        return conda.core.solve.LibSolvSolver
