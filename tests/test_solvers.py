# SPDX-License-Identifier: BSD-3-Clause

import collections
import contextlib
import functools
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
from conda.models.records import PackageRecord
from conda.resolve import MatchSpec

from . import helpers


@functools.lru_cache()
def index_packages(num):
    """Get the index data of the ``helpers.get_index_r_*`` helpers."""
    # XXX: get_index_r_X should probably be refactored to avoid loading the environment like this.
    get_index = getattr(helpers, f'get_index_r_{num}')
    index, _ = get_index(context.subdir)
    return index.values()


class TestEnvironment:
    REPO_DATA_KEYS = (
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

    def __init__(self, path, solver_class, subdirs=context.subdirs):
        self._path = pathlib.Path(path)
        self._solver_class = solver_class
        self.subdirs = subdirs
        self.repo_packages = []

    def solver(self, add, remove):
        self._write_packages()
        channels = tuple(
            # We use the ``test`` directory here to set the name of the channel.
            Channel('file://{}'.format(self._path / 'test' / subdir))
            for subdir in self.subdirs
        )
        return self._solver_class(
            prefix='dummy - does not exist',
            subdirs=self.subdirs,
            channels=channels,
            specs_to_add=add,
            specs_to_remove=remove,
        )

    def solver_transaction(self, add=(), remove=()):
        return self.solver(add=add, remove=remove).solve_final_state()

    def install(self, *specs):
        return self.solver_transaction(add=specs)

    def remove(self, *specs):
        return self.solver_transaction(remove=specs)

    def _write_packages(self):
        """Write packages to the channel path."""
        # build package data
        package_data = collections.defaultdict(dict)
        for record in self.repo_packages:
            package_data[record.subdir][record.fn] = {
                key: value
                for key, value in vars(record).items()
                if key in self.REPO_DATA_KEYS
            }
        # write repodata
        assert set(self.subdirs).issuperset(set(package_data.keys()))
        for subdir in self.subdirs:
            subdir_path = self._path / 'test' / subdir
            subdir_path.mkdir(parents=True, exist_ok=True)
            subdir_path.joinpath('repodata.json').write_text(json.dumps({
                'info': {
                    'subdir': subdir,
                },
                'packages': package_data.get(subdir, {}),
            }))


class SolverTests:
    """Tests for :py:class:`conda.core.solve.Solver` implementations."""

    @property
    def solver_class(self) -> Type[conda.core.solve.Solver]:
        """Class under test."""
        raise NotImplementedError

    @property
    def tests_to_skip(self):
        return {}  # skip reason -> list of tests to skip

    @pytest.fixture(autouse=True)
    def skip_tests(self, request):
        for reason, skip_list in self.tests_to_skip.items():
            if request.node.name in skip_list:
                pytest.skip(reason)

    @pytest.fixture()
    def env(self):
        with tempfile.TemporaryDirectory(prefix='conda-test-repo-') as tmpdir:
            yield TestEnvironment(tmpdir, self.solver_class)

    def package_string_set(self, packages):
        """Transforms package container in package string set."""
        return {
            f'{record.channel.name}::{record.name}-{record.version}-{record.build}'
            for record in packages
        }

    def assert_installs_expected(self, environment, specs, expecting):
        """Helper to assert that a transaction result contains the packages
        specified by the set of specification string."""
        installed = environment.install(*specs)
        assert installed, f'no installed specs ({installed})'
        assert self.package_string_set(installed) == set(expecting) | {
            # XXX: injected
            'test::distribute-0.6.36-py27_1',
            'test::pip-1.3.1-py27_1',
        }

    def assert_same_packages(self, packages1, packages2):
        assert self.package_string_set(packages1) == self.package_string_set(packages2)

    def assert_record_in(self, record_str, records):
        """Helper to assert that a record list contains a record matching the
        provided record string."""
        assert record_str in self.package_string_set(records)

    def assert_unsatisfiable(self, exc_info, entries):
        """Helper to assert that a :py:class:`conda.exceptions.UnsatisfiableError`
        instance as a the specified set of unsatisfiable specifications."""
        assert issubclass(exc_info.type, UnsatisfiableError)
        if exc_info.type is UnsatisfiableError:
            assert sorted(
                tuple(map(str, entries))
                for entries in exc_info.value.unsatisfiable
            ) == entries

    def test_empty(self, env):
        env.repo_packages = index_packages(1)
        assert env.install() == []

    def test_iopro_mkl(self, env):
        env.repo_packages = index_packages(1)
        self.assert_installs_expected(
            env,
            ['iopro 1.4*', 'python 2.7*', 'numpy 1.7*'],
            [
                'test::iopro-1.4.3-np17py27_p0',
                'test::numpy-1.7.1-py27_0',
                'test::openssl-1.0.1c-0',
                'test::python-2.7.5-0',
                'test::readline-6.2-0',
                'test::sqlite-3.7.13-0',
                'test::system-5.8-1',
                'test::tk-8.5.13-0',
                'test::unixodbc-2.3.1-0',
                'test::zlib-1.2.7-0',
            ],
        )

    def test_iopro_nomkl(self, env):
        env.repo_packages = index_packages(1)
        self.assert_installs_expected(
            env,
            ['iopro 1.4*', 'python 2.7*', 'numpy 1.7*', MatchSpec(track_features='mkl')],
            [
                'test::iopro-1.4.3-np17py27_p0',
                'test::mkl-rt-11.0-p0',
                'test::numpy-1.7.1-py27_p0',
                'test::openssl-1.0.1c-0',
                'test::python-2.7.5-0',
                'test::readline-6.2-0',
                'test::sqlite-3.7.13-0',
                'test::system-5.8-1',
                'test::tk-8.5.13-0',
                'test::unixodbc-2.3.1-0',
                'test::zlib-1.2.7-0',
            ],
        )

    def test_mkl(self, env):
        env.repo_packages = index_packages(1)
        self.assert_same_packages(
            env.install('mkl'),
            env.install('mkl 11*', MatchSpec(track_features='mkl')),
        )

    def test_accelerate(self, env):
        env.repo_packages = index_packages(1)
        self.assert_same_packages(
            env.install('accelerate'),
            env.install('accelerate', MatchSpec(track_features='mkl')),
        )

    def test_scipy_mkl(self, env):
        env.repo_packages = index_packages(1)
        records = env.install('scipy', 'python 2.7*', 'numpy 1.7*', MatchSpec(track_features='mkl'))

        for record in records:
            if record.name in ('numpy', 'scipy'):
                assert 'mkl' in record.features

        self.assert_record_in('test::numpy-1.7.1-py27_p0', records)
        self.assert_record_in('test::scipy-0.12.0-np17py27_p0', records)

    def test_anaconda_nomkl(self, env):
        env.repo_packages = index_packages(1)
        records = env.install('anaconda 1.5.0', 'python 2.7*', 'numpy 1.7*')
        assert len(records) == 107
        self.assert_record_in('test::scipy-0.12.0-np17py27_0', records)

    def test_pseudo_boolean(self, env):
        env.repo_packages = index_packages(1)
        # The latest version of iopro, 1.5.0, was not built against numpy 1.5
        self.assert_installs_expected(
            env,
            ['iopro', 'python 2.7*', 'numpy 1.5*'],
            [
                'test::iopro-1.4.3-np15py27_p0',
                'test::numpy-1.5.1-py27_4',
                'test::openssl-1.0.1c-0',
                'test::python-2.7.5-0',
                'test::readline-6.2-0',
                'test::sqlite-3.7.13-0',
                'test::system-5.8-1',
                'test::tk-8.5.13-0',
                'test::unixodbc-2.3.1-0',
                'test::zlib-1.2.7-0',
            ],
        )
        self.assert_installs_expected(
            env,
            ['iopro', 'python 2.7*', 'numpy 1.5*', MatchSpec(track_features='mkl')],
            [
                'test::iopro-1.4.3-np15py27_p0',
                'test::mkl-rt-11.0-p0',
                'test::numpy-1.5.1-py27_p4',
                'test::openssl-1.0.1c-0',
                'test::python-2.7.5-0',
                'test::readline-6.2-0',
                'test::sqlite-3.7.13-0',
                'test::system-5.8-1',
                'test::tk-8.5.13-0',
                'test::unixodbc-2.3.1-0',
                'test::zlib-1.2.7-0',
            ],
        )

    def test_unsat_from_r1(self, env):
        env.repo_packages = index_packages(1)

        with pytest.raises(UnsatisfiableError) as exc_info:
            env.install('numpy 1.5*', 'scipy 0.12.0b1')
        self.assert_unsatisfiable(exc_info, [
            ('numpy=1.5',),
            ('scipy==0.12.0b1', "numpy[version='1.6.*|1.7.*']"),
        ])

        with pytest.raises(UnsatisfiableError) as exc_info:
            env.install('numpy 1.5*', 'python 3*')
        self.assert_unsatisfiable(exc_info, [
            ('numpy=1.5', 'nose', 'python=3.3'),
            ('numpy=1.5', "python[version='2.6.*|2.7.*']"),
            ('python=3',),
        ])

        with pytest.raises((ResolvePackageNotFound, UnsatisfiableError)) as exc_info:
            env.install('numpy 1.5*', 'numpy 1.6*')
        if exc_info.type is ResolvePackageNotFound:
            assert sorted(map(str, exc_info.value.bad_deps)) == [
                "numpy[version='1.5.*,1.6.*']",
            ]

    def test_unsat_simple(self, env):
        env.repo_packages = [
            helpers.record(name='a', depends=['c >=1,<2']),
            helpers.record(name='b', depends=['c >=2,<3']),
            helpers.record(name='c', version='1.0'),
            helpers.record(name='c', version='2.0'),
        ]
        with pytest.raises(UnsatisfiableError) as exc_info:
            env.install('a', 'b')
        self.assert_unsatisfiable(exc_info, [
            ('a', "c[version='>=1,<2']"),
            ('b', "c[version='>=2,<3']"),
        ])

    def test_get_dists(self, env):
        env.repo_packages = index_packages(1)
        records = env.install('anaconda 1.4.0')
        assert 'test::anaconda-1.4.0-np17py27_0' in self.package_string_set(records)
        assert 'test::freetype-2.4.10-0' in self.package_string_set(records)

    def test_unsat_shortest_chain_1(self, env):
        env.repo_packages = [
            helpers.record(name='a', depends=['d', 'c <1.3.0']),
            helpers.record(name='b', depends=['c']),
            helpers.record(name='c', version='1.3.6',),
            helpers.record(name='c', version='1.2.8',),
            helpers.record(name='d', depends=['c >=0.8.0']),
        ]
        with pytest.raises(UnsatisfiableError) as exc_info:
            env.install('c=1.3.6', 'a', 'b')
        self.assert_unsatisfiable(exc_info, [
            ('a', "c[version='<1.3.0']"),
            ('a', 'd', "c[version='>=0.8.0']"),
            ('b', 'c'),
            ('c=1.3.6',),
        ])

    def test_unsat_shortest_chain_2(self, env):
        env.repo_packages = [
            helpers.record(name='a', depends=['d', 'c >=0.8.0']),
            helpers.record(name='b', depends=['c']),
            helpers.record(name='c', version='1.3.6',),
            helpers.record(name='c', version='1.2.8',),
            helpers.record(name='d', depends=['c <1.3.0']),
        ]
        with pytest.raises(UnsatisfiableError) as exc_info:
            env.install('c=1.3.6', 'a', 'b')
        self.assert_unsatisfiable(exc_info, [
            ('a', "c[version='>=0.8.0']"),
            ('a', 'd', "c[version='<1.3.0']"),
            ('b', 'c'),
            ('c=1.3.6',),
        ])

    def test_unsat_shortest_chain_3(self, env):
        env.repo_packages = [
            helpers.record(name='a', depends=['f', 'e']),
            helpers.record(name='b', depends=['c']),
            helpers.record(name='c', version='1.3.6',),
            helpers.record(name='c', version='1.2.8',),
            helpers.record(name='d', depends=['c >=0.8.0']),
            helpers.record(name='e', depends=['c <1.3.0']),
            helpers.record(name='f', depends=['d']),
        ]
        with pytest.raises(UnsatisfiableError) as exc_info:
            env.install('c=1.3.6', 'a', 'b')
        self.assert_unsatisfiable(exc_info, [
            ('a', 'e', "c[version='<1.3.0']"),
            ('b', 'c'),
            ('c=1.3.6',),
        ])

    def test_unsat_shortest_chain_4(self, env):
        env.repo_packages = [
            helpers.record(name='a', depends=['py =3.7.1']),
            helpers.record(name="py_req_1"),
            helpers.record(name="py_req_2"),
            helpers.record(name='py', version='3.7.1', depends=['py_req_1', 'py_req_2']),
            helpers.record(name='py', version='3.6.1', depends=['py_req_1', 'py_req_2']),
        ]
        with pytest.raises(UnsatisfiableError) as exc_info:
            env.install('a', 'py=3.6.1')
        self.assert_unsatisfiable(exc_info, [
            ('a', 'py=3.7.1'),
            ('py=3.6.1',),
        ])

    def test_unsat_chain(self, env):
        # a -> b -> c=1.x -> d=1.x
        # e      -> c=2.x -> d=2.x
        env.repo_packages = [
            helpers.record(name='a', depends=['b']),
            helpers.record(name='b', depends=['c >=1,<2']),
            helpers.record(name='c', version='1.0', depends=['d >=1,<2']),
            helpers.record(name='d', version='1.0'),

            helpers.record(name='e', depends=['c >=2,<3']),
            helpers.record(name='c', version='2.0', depends=['d >=2,<3']),
            helpers.record(name='d', version='2.0'),
        ]
        with pytest.raises(UnsatisfiableError) as exc_info:
            env.install('a', 'e')
        self.assert_unsatisfiable(exc_info, [
            ('a', 'b', "c[version='>=1,<2']"),
            ('e', "c[version='>=2,<3']"),
        ])

    def test_unsat_any_two_not_three(self, env):
        # can install any two of a, b and c but not all three
        env.repo_packages = [
            helpers.record(name='a', version='1.0', depends=['d >=1,<2']),
            helpers.record(name='a', version='2.0', depends=['d >=2,<3']),

            helpers.record(name='b', version='1.0', depends=['d >=1,<2']),
            helpers.record(name='b', version='2.0', depends=['d >=3,<4']),

            helpers.record(name='c', version='1.0', depends=['d >=2,<3']),
            helpers.record(name='c', version='2.0', depends=['d >=3,<4']),

            helpers.record(name='d', version='1.0'),
            helpers.record(name='d', version='2.0'),
            helpers.record(name='d', version='3.0'),
        ]
        # a and b can be installed
        installed = env.install('a', 'b')
        assert any(k.name == 'a' and k.version == '1.0' for k in installed)
        assert any(k.name == 'b' and k.version == '1.0' for k in installed)
        # a and c can be installed
        installed = env.install('a', 'c')
        assert any(k.name == 'a' and k.version == '2.0' for k in installed)
        assert any(k.name == 'c' and k.version == '1.0' for k in installed)
        # b and c can be installed
        installed = env.install('b', 'c')
        assert any(k.name == 'b' and k.version == '2.0' for k in installed)
        assert any(k.name == 'c' and k.version == '2.0' for k in installed)
        # a, b and c cannot be installed
        with pytest.raises(UnsatisfiableError) as exc_info:
            env.install('a', 'b', 'c')
        self.assert_unsatisfiable(exc_info, [
            ('a', "d[version='>=1,<2|>=2,<3']"),
            ('b', "d[version='>=1,<2|>=3,<4']"),
            ('c', "d[version='>=2,<3|>=3,<4']"),
        ])


class TestLegacySolver(SolverTests):
    @property
    def solver_class(self):
        return conda.core.solve.Solver


class TestLibSolvSolver(SolverTests):
    @property
    def solver_class(self):
        return conda.core.solve.LibSolvSolver

    @property
    def tests_to_skip(self):
        return {
            'LibSolvSolver does not support track-features/features': [
                'test_iopro_mkl',
                'test_iopro_nomkl',
                'test_mkl',
                'test_accelerate',
                'test_scipy_mkl',
                'test_pseudo_boolean',
            ]
        }
