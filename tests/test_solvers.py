# SPDX-License-Identifier: BSD-3-Clause

import collections
import contextlib
import json
import os
import pathlib
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
        """Class under test."""
        raise NotImplementedError

    def _write_channel_packages(self, channel_path: pathlib.Path, subdirs, packages):
        """Create a channel containing a set of packages."""
        # build package data
        package_data = collections.defaultdict(dict)
        for record in packages:
            package_data[record.subdir][record.fn] = {
                key: value
                for key, value in vars(record).items()
                if key in (
                    'build',
                    'build_number',
                    'depends',
                    'license',
                    'md5',
                    'name',
                    'sha256',
                    'size',
                    'subdir',
                    'timestamp',
                    'version',
                    'track_features',
                    'features',
                )
            }
        # write repodata
        for subdir in subdirs:
            subdir_path = channel_path / subdir
            subdir_path.mkdir(parents=True, exist_ok=True)
            subdir_path.joinpath('repodata.json').write_text(json.dumps({
                'info': {
                    'subdir': subdir,
                },
                'packages': package_data.get(subdir, {}),
            }))

    @contextlib.contextmanager
    def solver(self, *, add=(), remove=(), packages=()):
        """Create a new solver.

        Roughly equivalent to ``Solver(specs_to_add=..., specs_to_remove=...)``
        with a custom channel containing the data specified in `packages`.
        """
        with tempfile.TemporaryDirectory(prefix='conda-test-repo-') as tmpdir_path:
            tmpdir = pathlib.Path(tmpdir_path)
            channels = tuple(
                Channel(f'file://{tmpdir / subdir}')
                for subdir in context.subdirs
            )
            self._write_channel_packages(tmpdir, context.subdirs, list(packages))
            yield self.solver_class(
                prefix='dummy - does not exist',
                subdirs=context.subdirs,
                channels=channels,
                specs_to_add=add,
                specs_to_remove=remove,
            )

    def install(self, *specs, packages=None):
        """Try a install transaction in channel with a set of specified packages."""
        if not packages:
            packages = self.index(1)
        with self.solver(add=specs, packages=packages) as solver:
            return solver.solve_final_state()

    def index(self, num):
        """Get the index data of the ``helpers.get_index_r_*`` helpers."""
        # XXX: get_index_r_X should probably be refactored to avoid loading the environment like this.
        get_index = getattr(helpers, f'get_index_r_{num}')
        index, _ = get_index(context.subdir)
        return index.values()

    def package_string_set(self, packages):
        """Transforms package container in package string set."""
        return {
            f'{record.name}-{record.version}-{record.build}'
            for record in packages
        }

    def assert_installed(self, specs, expecting):
        """Helper to assert that a transaction result contains the packages
        specified by the set of specification string."""
        installed = self.install(*specs)
        assert installed, f'no installed specs ({installed})'
        assert self.package_string_set(installed) == set(expecting) | {
            # XXX: injected
            'distribute-0.6.36-py27_1',
            'pip-1.3.1-py27_1',
        }

    def assert_same_installed(self, specs1, specs2):
        assert self.package_string_set(
            self.install(*specs1),
        ) == self.package_string_set(
            self.install(*specs2),
        )

    def assert_record_in(self, record_str, records):
        """Helper to assert that a record list contains a record matching the
        provided record string."""
        assert record_str in [
            f'{record.name}-{record.version}-{record.build}' for record in records
        ]

    def assert_unsatisfiable(self, exc_info, entries):
        """Helper to assert that a :py:class:`conda.exceptions.UnsatisfiableError`
        instance as a the specified set of unsatisfiable specifications."""
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
                'iopro-1.4.3-np17py27_p0',
                'numpy-1.7.1-py27_0',
                'openssl-1.0.1c-0',
                'python-2.7.5-0',
                'readline-6.2-0',
                'sqlite-3.7.13-0',
                'system-5.8-1',
                'tk-8.5.13-0',
                'unixodbc-2.3.1-0',
                'zlib-1.2.7-0',
            ],
        )

    def test_mkl(self):
        self.assert_same_installed(['mkl'], [
            'mkl 11*', MatchSpec(track_features='mkl')
        ])

    def test_accelerate(self):
        self.assert_same_installed(['accelerate'], [
            'accelerate', MatchSpec(track_features='mkl')
        ])

    def test_scipy_mkl(self):
        records = self.install('scipy', 'python 2.7*', 'numpy 1.7*', MatchSpec(track_features='mkl'))

        for record in records:
            if record.name in ('numpy', 'scipy'):
                assert 'mkl' in record.features

        self.assert_record_in('numpy-1.7.1-py27_p0', records)
        self.assert_record_in('scipy-0.12.0-np17py27_p0', records)

    def test_anaconda_nomkl(self):
        records = self.install('anaconda 1.5.0', 'python 2.7*', 'numpy 1.7*')
        assert len(records) == 107
        self.assert_record_in('scipy-0.12.0-np17py27_0', records)

    def test_pseudo_boolean(self):
        # The latest version of iopro, 1.5.0, was not built against numpy 1.5
        self.assert_installed(
            ['iopro', 'python 2.7*', 'numpy 1.5*'], [
                'iopro-1.4.3-np15py27_p0',
                'numpy-1.5.1-py27_4',
                'openssl-1.0.1c-0',
                'python-2.7.5-0',
                'readline-6.2-0',
                'sqlite-3.7.13-0',
                'system-5.8-1',
                'tk-8.5.13-0',
                'unixodbc-2.3.1-0',
                'zlib-1.2.7-0',
            ],
        )
        self.assert_installed(
            ['iopro', 'python 2.7*', 'numpy 1.5*', MatchSpec(track_features='mkl')], [
                'iopro-1.4.3-np15py27_p0',
                'mkl-rt-11.0-p0',
                'numpy-1.5.1-py27_p4',
                'openssl-1.0.1c-0',
                'python-2.7.5-0',
                'readline-6.2-0',
                'sqlite-3.7.13-0',
                'system-5.8-1',
                'tk-8.5.13-0',
                'unixodbc-2.3.1-0',
                'zlib-1.2.7-0',
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
                    helpers.record(name='a', depends=['c >=1,<2']),
                    helpers.record(name='b', depends=['c >=2,<3']),
                    helpers.record(name='c', version='1.0'),
                    helpers.record(name='c', version='2.0'),
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
