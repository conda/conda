# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from contextlib import contextmanager
import os
from unittest import TestCase

from os.path import join

from conda.gateways.logging import TRACE
import pytest

from conda.base.context import context, reset_context, Context
from conda.common.io import env_var, env_vars, stderr_log_level
from conda.core.linked_data import PrefixData
from conda.core.solve import DepsModifier, Solver
from conda.exceptions import UnsatisfiableError
from conda.history import History
from conda.models.channel import Channel
from conda.models.dag import PrefixDag
from conda.models.dist import Dist
from conda.models.prefix_record import PrefixRecord
from conda.resolve import MatchSpec
from ..helpers import patch, get_index_r_1, get_index_r_2, get_index_r_3, get_index_r_4
from conda.common.compat import iteritems

try:
    from unittest.mock import Mock, patch
except ImportError:
    from mock import Mock, patch

TEST_PREFIX = '/a/test/c/prefix'


@contextmanager
def get_solver(specs_to_add=(), specs_to_remove=(), prefix_records=(), history_specs=()):
    PrefixData._cache_ = {}
    pd = PrefixData(TEST_PREFIX)
    pd._PrefixData__prefix_records = {rec.name: PrefixRecord.from_objects(rec) for rec in prefix_records}
    spec_map = {spec.name: spec for spec in history_specs}
    get_index_r_1()
    with patch.object(History, 'get_requested_specs_map', return_value=spec_map):
        solver = Solver(TEST_PREFIX, (Channel('channel-1'),), (context.subdir,),
                        specs_to_add=specs_to_add, specs_to_remove=specs_to_remove)
        yield solver


@contextmanager
def get_solver_2(specs_to_add=(), specs_to_remove=(), prefix_records=(), history_specs=()):
    PrefixData._cache_ = {}
    pd = PrefixData(TEST_PREFIX)
    pd._PrefixData__prefix_records = {rec.name: PrefixRecord.from_objects(rec) for rec in prefix_records}
    spec_map = {spec.name: spec for spec in history_specs}
    get_index_r_2()
    with patch.object(History, 'get_requested_specs_map', return_value=spec_map):
        solver = Solver(TEST_PREFIX, (Channel('channel-2'),), (context.subdir,),
                        specs_to_add=specs_to_add, specs_to_remove=specs_to_remove)
        yield solver


@contextmanager
def get_solver_3(specs_to_add=(), specs_to_remove=(), prefix_records=(), history_specs=()):
    PrefixData._cache_ = {}
    pd = PrefixData(TEST_PREFIX)
    pd._PrefixData__prefix_records = {rec.name: PrefixRecord.from_objects(rec) for rec in prefix_records}
    spec_map = {spec.name: spec for spec in history_specs}
    get_index_r_3()
    with patch.object(History, 'get_requested_specs_map', return_value=spec_map):
        solver = Solver(TEST_PREFIX, (Channel('channel-3'),), (context.subdir,),
                        specs_to_add=specs_to_add, specs_to_remove=specs_to_remove)
        yield solver


@contextmanager
def get_solver_4(specs_to_add=(), specs_to_remove=(), prefix_records=(), history_specs=()):
    PrefixData._cache_ = {}
    pd = PrefixData(TEST_PREFIX)
    pd._PrefixData__prefix_records = {rec.name: PrefixRecord.from_objects(rec) for rec in prefix_records}
    spec_map = {spec.name: spec for spec in history_specs}
    get_index_r_4()
    with patch.object(History, 'get_requested_specs_map', return_value=spec_map):
        solver = Solver(TEST_PREFIX, (Channel('channel-4'),), (context.subdir,),
                        specs_to_add=specs_to_add, specs_to_remove=specs_to_remove)
        yield solver


@contextmanager
def get_solver_aggregate_1(specs_to_add=(), specs_to_remove=(), prefix_records=(), history_specs=()):
    PrefixData._cache_ = {}
    pd = PrefixData(TEST_PREFIX)
    pd._PrefixData__prefix_records = {rec.name: PrefixRecord.from_objects(rec) for rec in prefix_records}
    spec_map = {spec.name: spec for spec in history_specs}
    get_index_r_2()
    get_index_r_4()
    with patch.object(History, 'get_requested_specs_map', return_value=spec_map):
        solver = Solver(TEST_PREFIX, (Channel('channel-2'), Channel('channel-4'), ),
                        (context.subdir,), specs_to_add=specs_to_add, specs_to_remove=specs_to_remove)
        yield solver


def test_solve_1():
    specs = MatchSpec("numpy"),

    with get_solver(specs) as solver:
        final_state = solver.solve_final_state()
        print([Dist(rec).full_name for rec in final_state])
        order = (
            'channel-1::openssl-1.0.1c-0',
            'channel-1::readline-6.2-0',
            'channel-1::sqlite-3.7.13-0',
            'channel-1::system-5.8-1',
            'channel-1::tk-8.5.13-0',
            'channel-1::zlib-1.2.7-0',
            'channel-1::python-3.3.2-0',
            'channel-1::numpy-1.7.1-py33_0',
        )
        assert tuple(final_state) == tuple(solver._index[Dist(d)] for d in order)

    specs_to_add = MatchSpec("python=2"),
    with get_solver(specs_to_add=specs_to_add,
                    prefix_records=final_state, history_specs=specs) as solver:
        final_state = solver.solve_final_state()
        print([Dist(rec).full_name for rec in final_state])
        order = (
            'channel-1::openssl-1.0.1c-0',
            'channel-1::readline-6.2-0',
            'channel-1::sqlite-3.7.13-0',
            'channel-1::system-5.8-1',
            'channel-1::tk-8.5.13-0',
            'channel-1::zlib-1.2.7-0',
            'channel-1::python-2.7.5-0',
            'channel-1::numpy-1.7.1-py27_0',
        )
        assert tuple(final_state) == tuple(solver._index[Dist(d)] for d in order)


def test_prune_1():
    specs = MatchSpec("numpy=1.6"), MatchSpec("python=2.7.3"), MatchSpec("accelerate"),

    with get_solver(specs) as solver:
        final_state_1 = solver.solve_final_state()
        # PrefixDag(final_state_1, specs).open_url()
        print([Dist(rec).full_name for rec in final_state_1])
        order = (
            'channel-1::libnvvm-1.0-p0',
            'channel-1::openssl-1.0.1c-0',
            'channel-1::readline-6.2-0',
            'channel-1::sqlite-3.7.13-0',
            'channel-1::system-5.8-1',
            'channel-1::tk-8.5.13-0',
            'channel-1::zlib-1.2.7-0',
            'channel-1::llvm-3.2-0',
            'channel-1::mkl-rt-11.0-p0',
            'channel-1::python-2.7.3-7',
            'channel-1::bitarray-0.8.1-py27_0',
            'channel-1::llvmpy-0.11.2-py27_0',
            'channel-1::meta-0.4.2.dev-py27_0',
            'channel-1::mkl-service-1.0.0-py27_p0',
            'channel-1::numpy-1.6.2-py27_p4',
            'channel-1::numba-0.8.1-np16py27_0',
            'channel-1::numexpr-2.1-np16py27_p0',
            'channel-1::scipy-0.12.0-np16py27_p0',
            'channel-1::numbapro-0.11.0-np16py27_p0',
            'channel-1::scikit-learn-0.13.1-np16py27_p0',
            'channel-1::mkl-11.0-np16py27_p0',
            'channel-1::accelerate-1.1.0-np16py27_p0',
        )
        assert tuple(final_state_1) == tuple(solver._index[Dist(d)] for d in order)

    specs_to_remove = MatchSpec("numbapro"),
    with get_solver(specs_to_remove=specs_to_remove, prefix_records=final_state_1,
                    history_specs=specs) as solver:
        final_state_2 = solver.solve_final_state(prune=False)
        # PrefixDag(final_state_2, specs).open_url()
        print([Dist(rec).full_name for rec in final_state_2])
        order = (
            'channel-1::libnvvm-1.0-p0',
            'channel-1::openssl-1.0.1c-0',
            'channel-1::readline-6.2-0',
            'channel-1::sqlite-3.7.13-0',
            'channel-1::system-5.8-1',
            'channel-1::tk-8.5.13-0',
            'channel-1::zlib-1.2.7-0',
            'channel-1::llvm-3.2-0',
            'channel-1::mkl-rt-11.0-p0',
            'channel-1::python-2.7.3-7',
            'channel-1::bitarray-0.8.1-py27_0',
            'channel-1::llvmpy-0.11.2-py27_0',
            'channel-1::meta-0.4.2.dev-py27_0',
            'channel-1::mkl-service-1.0.0-py27_p0',
            'channel-1::numpy-1.6.2-py27_p4',
            'channel-1::numba-0.8.1-np16py27_0',
            'channel-1::numexpr-2.1-np16py27_p0',
            'channel-1::scipy-0.12.0-np16py27_p0',
            'channel-1::scikit-learn-0.13.1-np16py27_p0',
            'channel-1::mkl-11.0-np16py27_p0',
        )
        assert tuple(final_state_2) == tuple(solver._index[Dist(d)] for d in order)

    with get_solver(specs_to_remove=specs_to_remove, prefix_records=final_state_1,
                    history_specs=specs) as solver:
        final_state_2 = solver.solve_final_state(prune=True)
        # PrefixDag(final_state_2, specs).open_url()
        print([Dist(rec).full_name for rec in final_state_2])
        order = (
            'channel-1::openssl-1.0.1c-0',
            'channel-1::readline-6.2-0',
            'channel-1::sqlite-3.7.13-0',
            'channel-1::system-5.8-1',
            'channel-1::tk-8.5.13-0',
            'channel-1::zlib-1.2.7-0',
            'channel-1::python-2.7.3-7',
            'channel-1::numpy-1.6.2-py27_4',
        )
        assert tuple(final_state_2) == tuple(solver._index[Dist(d)] for d in order)


def test_force_remove_1():
    specs = MatchSpec("numpy[build=*py27*]"),
    with get_solver(specs) as solver:
        final_state_1 = solver.solve_final_state()
        # PrefixDag(final_state_1, specs).open_url()
        print([Dist(rec).full_name for rec in final_state_1])
        order = (
            'channel-1::openssl-1.0.1c-0',
            'channel-1::readline-6.2-0',
            'channel-1::sqlite-3.7.13-0',
            'channel-1::system-5.8-1',
            'channel-1::tk-8.5.13-0',
            'channel-1::zlib-1.2.7-0',
            'channel-1::python-2.7.5-0',
            'channel-1::numpy-1.7.1-py27_0',
        )
        assert tuple(final_state_1) == tuple(solver._index[Dist(d)] for d in order)

    specs_to_remove = MatchSpec("python"),
    with get_solver(specs_to_remove=specs_to_remove, prefix_records=final_state_1,
                    history_specs=specs) as solver:
        final_state_2 = solver.solve_final_state()
        # PrefixDag(final_state_2, specs).open_url()
        print([Dist(rec).full_name for rec in final_state_2])
        order = (
            'channel-1::openssl-1.0.1c-0',
            'channel-1::readline-6.2-0',
            'channel-1::sqlite-3.7.13-0',
            'channel-1::system-5.8-1',
            'channel-1::tk-8.5.13-0',
            'channel-1::zlib-1.2.7-0',
        )
        assert tuple(final_state_2) == tuple(solver._index[Dist(d)] for d in order)

    specs_to_remove = MatchSpec("python"),
    with get_solver(specs_to_remove=specs_to_remove, prefix_records=final_state_1,
                    history_specs=specs) as solver:
        final_state_2 = solver.solve_final_state(force_remove=True)
        # PrefixDag(final_state_2, specs).open_url()
        print([Dist(rec).full_name for rec in final_state_2])
        order = (
            'channel-1::openssl-1.0.1c-0',
            'channel-1::readline-6.2-0',
            'channel-1::sqlite-3.7.13-0',
            'channel-1::system-5.8-1',
            'channel-1::tk-8.5.13-0',
            'channel-1::zlib-1.2.7-0',
            'channel-1::numpy-1.7.1-py27_0',
        )
        assert tuple(final_state_2) == tuple(solver._index[Dist(d)] for d in order)

    with get_solver(prefix_records=final_state_2) as solver:
        final_state_3 = solver.solve_final_state(prune=True)
        # PrefixDag(final_state_2, specs).open_url()
        print([Dist(rec).full_name for rec in final_state_3])
        order = ()
        assert tuple(final_state_3) == tuple(solver._index[Dist(d)] for d in order)


def test_no_deps_1():
    specs = MatchSpec("python=2"),
    with get_solver(specs) as solver:
        final_state_1 = solver.solve_final_state()
        # PrefixDag(final_state_1, specs).open_url()
        # print([Dist(rec).full_name for rec in final_state_1])
        order = (
            'channel-1::openssl-1.0.1c-0',
            'channel-1::readline-6.2-0',
            'channel-1::sqlite-3.7.13-0',
            'channel-1::system-5.8-1',
            'channel-1::tk-8.5.13-0',
            'channel-1::zlib-1.2.7-0',
            'channel-1::python-2.7.5-0',
        )
        assert tuple(final_state_1) == tuple(solver._index[Dist(d)] for d in order)

    specs_to_add = MatchSpec("numba"),
    with get_solver(specs_to_add, prefix_records=final_state_1, history_specs=specs) as solver:
        final_state_2 = solver.solve_final_state()
        # PrefixDag(final_state_2, specs).open_url()
        print([Dist(rec).full_name for rec in final_state_2])
        order = (
            'channel-1::openssl-1.0.1c-0',
            'channel-1::readline-6.2-0',
            'channel-1::sqlite-3.7.13-0',
            'channel-1::system-5.8-1',
            'channel-1::tk-8.5.13-0',
            'channel-1::zlib-1.2.7-0',
            'channel-1::llvm-3.2-0',
            'channel-1::python-2.7.5-0',
            'channel-1::llvmpy-0.11.2-py27_0',
            'channel-1::meta-0.4.2.dev-py27_0',
            'channel-1::numpy-1.7.1-py27_0',
            'channel-1::numba-0.8.1-np17py27_0'
        )
        assert tuple(final_state_2) == tuple(solver._index[Dist(d)] for d in order)

    specs_to_add = MatchSpec("numba"),
    with get_solver(specs_to_add, prefix_records=final_state_1, history_specs=specs) as solver:
        final_state_2 = solver.solve_final_state(deps_modifier='NO_DEPS')
        # PrefixDag(final_state_2, specs).open_url()
        print([Dist(rec).full_name for rec in final_state_2])
        order = (
            'channel-1::openssl-1.0.1c-0',
            'channel-1::readline-6.2-0',
            'channel-1::sqlite-3.7.13-0',
            'channel-1::system-5.8-1',
            'channel-1::tk-8.5.13-0',
            'channel-1::zlib-1.2.7-0',
            'channel-1::python-2.7.5-0',
            'channel-1::numba-0.8.1-np17py27_0',
        )
        assert tuple(final_state_2) == tuple(solver._index[Dist(d)] for d in order)


def test_only_deps_1():
    specs = MatchSpec("numba[build=*py27*]"),
    with get_solver(specs) as solver:
        final_state_1 = solver.solve_final_state(deps_modifier=DepsModifier.ONLY_DEPS)
        # PrefixDag(final_state_1, specs).open_url()
        # print([Dist(rec).full_name for rec in final_state_1])
        order = (
            'channel-1::openssl-1.0.1c-0',
            'channel-1::readline-6.2-0',
            'channel-1::sqlite-3.7.13-0',
            'channel-1::system-5.8-1',
            'channel-1::tk-8.5.13-0',
            'channel-1::zlib-1.2.7-0',
            'channel-1::llvm-3.2-0',
            'channel-1::python-2.7.5-0',
            'channel-1::llvmpy-0.11.2-py27_0',
            'channel-1::meta-0.4.2.dev-py27_0',
            'channel-1::numpy-1.7.1-py27_0',
        )
        assert tuple(final_state_1) == tuple(solver._index[Dist(d)] for d in order)


def test_only_deps_2():
    specs = MatchSpec("numpy=1.5"), MatchSpec("python=2.7.3"),
    with get_solver(specs) as solver:
        final_state_1 = solver.solve_final_state()
        # PrefixDag(final_state_1, specs).open_url()
        print([Dist(rec).full_name for rec in final_state_1])
        order = (
            'channel-1::openssl-1.0.1c-0',
            'channel-1::readline-6.2-0',
            'channel-1::sqlite-3.7.13-0',
            'channel-1::system-5.8-1',
            'channel-1::tk-8.5.13-0',
            'channel-1::zlib-1.2.7-0',
            'channel-1::python-2.7.3-7',
            'channel-1::numpy-1.5.1-py27_4',
        )
        assert tuple(final_state_1) == tuple(solver._index[Dist(d)] for d in order)

    specs_to_add = MatchSpec("numba=0.5"),
    with get_solver(specs_to_add) as solver:
        final_state_2 = solver.solve_final_state(deps_modifier=DepsModifier.ONLY_DEPS)
        # PrefixDag(final_state_2, specs).open_url()
        print([Dist(rec).full_name for rec in final_state_2])
        order = (
            'channel-1::openssl-1.0.1c-0',
            'channel-1::readline-6.2-0',
            'channel-1::sqlite-3.7.13-0',
            'channel-1::system-5.8-1',
            'channel-1::tk-8.5.13-0',
            'channel-1::zlib-1.2.7-0',
            'channel-1::llvm-3.2-0',
            'channel-1::python-2.7.5-0',
            'channel-1::llvmpy-0.10.0-py27_0',
            'channel-1::meta-0.4.2.dev-py27_0',
            'channel-1::nose-1.3.0-py27_0',
            'channel-1::numpy-1.7.1-py27_0',
            # 'channel-1::numba-0.5.0-np17py27_0',
        )
        assert tuple(final_state_2) == tuple(solver._index[Dist(d)] for d in order)

    specs_to_add = MatchSpec("numba=0.5"),
    with get_solver(specs_to_add, prefix_records=final_state_1, history_specs=specs) as solver:
        final_state_2 = solver.solve_final_state(deps_modifier=DepsModifier.ONLY_DEPS)
        # PrefixDag(final_state_2, specs).open_url()
        print([Dist(rec).full_name for rec in final_state_2])
        order = (
            'channel-1::openssl-1.0.1c-0',
            'channel-1::readline-6.2-0',
            'channel-1::sqlite-3.7.13-0',
            'channel-1::system-5.8-1',
            'channel-1::tk-8.5.13-0',
            'channel-1::zlib-1.2.7-0',
            'channel-1::llvm-3.2-0',
            'channel-1::python-2.7.3-7',
            'channel-1::llvmpy-0.10.0-py27_0',
            'channel-1::meta-0.4.2.dev-py27_0',
            'channel-1::nose-1.3.0-py27_0',
            'channel-1::numpy-1.7.1-py27_0',
            # 'channel-1::numba-0.5.0-np17py27_0',
        )
        assert tuple(final_state_2) == tuple(solver._index[Dist(d)] for d in order)


def test_update_all_1():
    specs = MatchSpec("numpy=1.5"), MatchSpec("python=2.6"), MatchSpec("system[build_number=0]")
    with get_solver(specs) as solver:
        final_state_1 = solver.solve_final_state()
        # PrefixDag(final_state_1, specs).open_url()
        print([Dist(rec).full_name for rec in final_state_1])
        order = (
            'channel-1::openssl-1.0.1c-0',
            'channel-1::readline-6.2-0',
            'channel-1::sqlite-3.7.13-0',
            'channel-1::system-5.8-0',
            'channel-1::tk-8.5.13-0',
            'channel-1::zlib-1.2.7-0',
            'channel-1::python-2.6.8-6',
            'channel-1::numpy-1.5.1-py26_4',
        )
        assert tuple(final_state_1) == tuple(solver._index[Dist(d)] for d in order)

    specs_to_add = MatchSpec("numba=0.6"), MatchSpec("numpy")
    with get_solver(specs_to_add, prefix_records=final_state_1, history_specs=specs) as solver:
        final_state_2 = solver.solve_final_state()
        # PrefixDag(final_state_2, specs).open_url()
        print([Dist(rec).full_name for rec in final_state_2])
        order = (
            'channel-1::openssl-1.0.1c-0',
            'channel-1::readline-6.2-0',
            'channel-1::sqlite-3.7.13-0',
            'channel-1::system-5.8-0',
            'channel-1::tk-8.5.13-0',
            'channel-1::zlib-1.2.7-0',
            'channel-1::llvm-3.2-0',
            'channel-1::python-2.6.8-6',
            'channel-1::llvmpy-0.10.2-py26_0',
            'channel-1::nose-1.3.0-py26_0',
            'channel-1::numpy-1.7.1-py26_0',
            'channel-1::numba-0.6.0-np17py26_0',
        )
        assert tuple(final_state_2) == tuple(solver._index[Dist(d)] for d in order)

    specs_to_add = MatchSpec("numba=0.6"),
    with get_solver(specs_to_add, prefix_records=final_state_1, history_specs=specs) as solver:
        final_state_2 = solver.solve_final_state(deps_modifier=DepsModifier.UPDATE_ALL)
        # PrefixDag(final_state_2, specs).open_url()
        print([Dist(rec).full_name for rec in final_state_2])
        order = (
            'channel-1::openssl-1.0.1c-0',
            'channel-1::readline-6.2-0',
            'channel-1::sqlite-3.7.13-0',
            'channel-1::system-5.8-1',
            'channel-1::tk-8.5.13-0',
            'channel-1::zlib-1.2.7-0',
            'channel-1::llvm-3.2-0',
            'channel-1::python-2.7.5-0',
            'channel-1::llvmpy-0.10.2-py27_0',
            'channel-1::meta-0.4.2.dev-py27_0',
            'channel-1::nose-1.3.0-py27_0',
            'channel-1::numpy-1.7.1-py27_0',
            'channel-1::numba-0.6.0-np17py27_0'
        )
        assert tuple(final_state_2) == tuple(solver._index[Dist(d)] for d in order)


def test_broken_install():
    specs = MatchSpec("pandas"), MatchSpec("python=2.7"), MatchSpec("numpy 1.6.*")
    with get_solver(specs) as solver:
        final_state_1 = solver.solve_final_state()
        # PrefixDag(final_state_1, specs).open_url()
        print([Dist(rec).full_name for rec in final_state_1])
        order_original = [
            'channel-1::openssl-1.0.1c-0',
            'channel-1::readline-6.2-0',
            'channel-1::sqlite-3.7.13-0',
            'channel-1::system-5.8-1',
            'channel-1::tk-8.5.13-0',
            'channel-1::zlib-1.2.7-0',
            'channel-1::python-2.7.5-0',
            'channel-1::numpy-1.6.2-py27_4',
            'channel-1::pytz-2013b-py27_0',
            'channel-1::six-1.3.0-py27_0',
            'channel-1::dateutil-2.1-py27_1',
            'channel-1::scipy-0.12.0-np16py27_0',
            'channel-1::pandas-0.11.0-np16py27_1',
        ]
        assert tuple(final_state_1) == tuple(solver._index[Dist(d)] for d in order_original)
        assert solver._r.environment_is_consistent(order_original)

    # Add an incompatible numpy; installation should be untouched
    order_1 = list(order_original)
    order_1[7] = "channel-1::numpy-1.7.1-py33_p0"
    order_1_records = [solver._index[Dist(d)] for d in order_1]
    assert not solver._r.environment_is_consistent(order_1)

    specs_to_add = MatchSpec("flask"),
    with get_solver(specs_to_add, prefix_records=order_1_records, history_specs=specs) as solver:
        final_state_2 = solver.solve_final_state()
        # PrefixDag(final_state_2, specs).open_url()
        print([Dist(rec).full_name for rec in final_state_2])
        order = [
            'channel-1::openssl-1.0.1c-0',
            'channel-1::readline-6.2-0',
            'channel-1::sqlite-3.7.13-0',
            'channel-1::system-5.8-1',
            'channel-1::tk-8.5.13-0',
            'channel-1::zlib-1.2.7-0',
            'channel-1::python-2.7.5-0',
            'channel-1::jinja2-2.6-py27_0',
            "channel-1::numpy-1.7.1-py33_p0",
            'channel-1::pytz-2013b-py27_0',
            'channel-1::six-1.3.0-py27_0',
            'channel-1::werkzeug-0.8.3-py27_0',
            'channel-1::dateutil-2.1-py27_1',
            'channel-1::flask-0.9-py27_0',
            'channel-1::scipy-0.12.0-np16py27_0',
            'channel-1::pandas-0.11.0-np16py27_1'
        ]
        assert tuple(final_state_2) == tuple(solver._index[Dist(d)] for d in order)
        assert not solver._r.environment_is_consistent(order)

    # adding numpy spec again snaps the packages back to a consistent state
    specs_to_add = MatchSpec("flask"), MatchSpec("numpy 1.6.*"),
    with get_solver(specs_to_add, prefix_records=order_1_records, history_specs=specs) as solver:
        final_state_2 = solver.solve_final_state()
        # PrefixDag(final_state_2, specs).open_url()
        print([Dist(rec).full_name for rec in final_state_2])
        order = [
            'channel-1::openssl-1.0.1c-0',
            'channel-1::readline-6.2-0',
            'channel-1::sqlite-3.7.13-0',
            'channel-1::system-5.8-1',
            'channel-1::tk-8.5.13-0',
            'channel-1::zlib-1.2.7-0',
            'channel-1::python-2.7.5-0',
            'channel-1::jinja2-2.6-py27_0',
            'channel-1::numpy-1.6.2-py27_4',
            'channel-1::pytz-2013b-py27_0',
            'channel-1::six-1.3.0-py27_0',
            'channel-1::werkzeug-0.8.3-py27_0',
            'channel-1::dateutil-2.1-py27_1',
            'channel-1::flask-0.9-py27_0',
            'channel-1::scipy-0.12.0-np16py27_0',
            'channel-1::pandas-0.11.0-np16py27_1',
        ]
        assert tuple(final_state_2) == tuple(solver._index[Dist(d)] for d in order)
        assert solver._r.environment_is_consistent(order)

    # Add an incompatible pandas; installation should be untouched, then fixed
    order_2 = list(order_original)
    order_2[12] = 'channel-1::pandas-0.11.0-np17py27_1'
    order_2_records = [solver._index[Dist(d)] for d in order_2]
    assert not solver._r.environment_is_consistent(order_2)

    specs_to_add = MatchSpec("flask"),
    with get_solver(specs_to_add, prefix_records=order_2_records, history_specs=specs) as solver:
        final_state_2 = solver.solve_final_state()
        # PrefixDag(final_state_2, specs).open_url()
        print([Dist(rec).full_name for rec in final_state_2])
        order = [
            'channel-1::openssl-1.0.1c-0',
            'channel-1::readline-6.2-0',
            'channel-1::sqlite-3.7.13-0',
            'channel-1::system-5.8-1',
            'channel-1::tk-8.5.13-0',
            'channel-1::zlib-1.2.7-0',
            'channel-1::python-2.7.5-0',
            'channel-1::jinja2-2.6-py27_0',
            'channel-1::numpy-1.6.2-py27_4',
            'channel-1::pytz-2013b-py27_0',
            'channel-1::six-1.3.0-py27_0',
            'channel-1::werkzeug-0.8.3-py27_0',
            'channel-1::dateutil-2.1-py27_1',
            'channel-1::flask-0.9-py27_0',
            'channel-1::scipy-0.12.0-np16py27_0',
            'channel-1::pandas-0.11.0-np17py27_1',
        ]
        assert tuple(final_state_2) == tuple(solver._index[Dist(d)] for d in order)
        assert not solver._r.environment_is_consistent(order)

    # adding pandas spec again snaps the packages back to a consistent state
    specs_to_add = MatchSpec("flask"), MatchSpec("pandas"),
    with get_solver(specs_to_add, prefix_records=order_2_records, history_specs=specs) as solver:
        final_state_2 = solver.solve_final_state()
        # PrefixDag(final_state_2, specs).open_url()
        print([Dist(rec).full_name for rec in final_state_2])
        order = [
            'channel-1::openssl-1.0.1c-0',
            'channel-1::readline-6.2-0',
            'channel-1::sqlite-3.7.13-0',
            'channel-1::system-5.8-1',
            'channel-1::tk-8.5.13-0',
            'channel-1::zlib-1.2.7-0',
            'channel-1::python-2.7.5-0',
            'channel-1::jinja2-2.6-py27_0',
            'channel-1::numpy-1.6.2-py27_4',
            'channel-1::pytz-2013b-py27_0',
            'channel-1::six-1.3.0-py27_0',
            'channel-1::werkzeug-0.8.3-py27_0',
            'channel-1::dateutil-2.1-py27_1',
            'channel-1::flask-0.9-py27_0',
            'channel-1::scipy-0.12.0-np16py27_0',
            'channel-1::pandas-0.11.0-np16py27_1',
        ]
        assert tuple(final_state_2) == tuple(solver._index[Dist(d)] for d in order)
        assert solver._r.environment_is_consistent(order)

    # Actually I think this part might be wrong behavior:
    #    # Removing pandas should fix numpy, since pandas depends on it
    # I think removing pandas should probably leave the broken numpy. That seems more consistent.

    # order_3 = list(order_original)
    # order_1[7] = 'channel-1::numpy-1.7.1-py33_p0'
    # order_3[12] = 'channel-1::pandas-0.11.0-np17py27_1'
    # order_3_records = [index[Dist(d)] for d in order_3]
    # assert not r.environment_is_consistent(order_3)
    #
    # PrefixData._cache_ = {}
    # pd = PrefixData(prefix)
    # pd._PrefixData__prefix_records = {rec.name: PrefixRecord.from_objects(rec)
    #                                   for rec in order_3_records}
    # spec_map = {
    #     "pandas": MatchSpec("pandas"),
    #     "python": MatchSpec("python=2.7"),
    #     "numpy": MatchSpec("numpy 1.6.*"),
    # }
    # with patch.object(History, 'get_requested_specs_map', return_value=spec_map):
    #     solver = Solver(prefix, (Channel('defaults'),), context.subdirs,
    #                     specs_to_remove=(MatchSpec("pandas"),))
    #     solver.index = index
    #     solver.r = r
    #     solver._prepared = True
    #
    #     final_state_2 = solver.solve_final_state()
    #
    #     # PrefixDag(final_state_2, specs).open_url()
    #     print([Dist(rec).full_name for rec in final_state_2])
    #
    #     order = [
    #         'channel-1::openssl-1.0.1c-0',
    #         'channel-1::readline-6.2-0',
    #         'channel-1::sqlite-3.7.13-0',
    #         'channel-1::system-5.8-1',
    #         'channel-1::tk-8.5.13-0',
    #         'channel-1::zlib-1.2.7-0',
    #         'channel-1::python-2.7.5-0',
    #         'channel-1::jinja2-2.6-py27_0',
    #         'channel-1::numpy-1.6.2-py27_4',
    #         'channel-1::pytz-2013b-py27_0',
    #         'channel-1::six-1.3.0-py27_0',
    #         'channel-1::werkzeug-0.8.3-py27_0',
    #         'channel-1::dateutil-2.1-py27_1',
    #         'channel-1::flask-0.9-py27_0',
    #         'channel-1::scipy-0.12.0-np16py27_0',
    #     ]
    #     assert tuple(final_state_2) == tuple(solver._index[Dist(d)] for d in order)
    #     assert r.environment_is_consistent(order)


def test_install_uninstall_features_1():
    specs = MatchSpec("pandas"), MatchSpec("python=2.7"), MatchSpec("numpy 1.6.*")
    with env_var("CONDA_TRACK_FEATURES", 'mkl', reset_context):
        with get_solver(specs) as solver:
            final_state_1 = solver.solve_final_state()
            # PrefixDag(final_state_1, specs).open_url()
            print([Dist(rec).full_name for rec in final_state_1])
            order = (
                'channel-1::openssl-1.0.1c-0',
                'channel-1::readline-6.2-0',
                'channel-1::sqlite-3.7.13-0',
                'channel-1::system-5.8-1',
                'channel-1::tk-8.5.13-0',
                'channel-1::zlib-1.2.7-0',
                'channel-1::mkl-rt-11.0-p0',
                'channel-1::python-2.7.5-0',
                'channel-1::numpy-1.6.2-py27_p4',
                'channel-1::pytz-2013b-py27_0',
                'channel-1::six-1.3.0-py27_0',
                'channel-1::dateutil-2.1-py27_1',
                'channel-1::scipy-0.12.0-np16py27_p0',
                'channel-1::pandas-0.11.0-np16py27_1',
            )
            assert tuple(final_state_1) == tuple(solver._index[Dist(d)] for d in order)

    # no more track_features in configuration
    # just remove the pandas package, but the mkl feature "stays in the environment"
    # that is, the current mkl packages aren't switched out
    specs_to_remove = MatchSpec("pandas"),
    with get_solver(specs_to_remove=specs_to_remove, prefix_records=final_state_1,
                    history_specs=specs) as solver:
        final_state_2 = solver.solve_final_state()
        # PrefixDag(final_state_2, specs).open_url()
        print([Dist(rec).full_name for rec in final_state_2])
        order = (
            'channel-1::openssl-1.0.1c-0',
            'channel-1::readline-6.2-0',
            'channel-1::sqlite-3.7.13-0',
            'channel-1::system-5.8-1',
            'channel-1::tk-8.5.13-0',
            'channel-1::zlib-1.2.7-0',
            'channel-1::mkl-rt-11.0-p0',
            'channel-1::python-2.7.5-0',
            'channel-1::numpy-1.6.2-py27_p4',
            'channel-1::pytz-2013b-py27_0',
            'channel-1::six-1.3.0-py27_0',
            'channel-1::dateutil-2.1-py27_1',
            'channel-1::scipy-0.12.0-np16py27_p0',
        )
        assert tuple(final_state_2) == tuple(solver._index[Dist(d)] for d in order)

    # now remove the mkl feature
    specs_to_remove = MatchSpec(provides_features="mkl"),
    history_specs = MatchSpec("python=2.7"), MatchSpec("numpy 1.6.*")
    with get_solver(specs_to_remove=specs_to_remove, prefix_records=final_state_2,
                    history_specs=history_specs) as solver:
        final_state_2 = solver.solve_final_state()
        # PrefixDag(final_state_2, specs).open_url()
        print([Dist(rec).full_name for rec in final_state_2])
        order = (
            'channel-1::openssl-1.0.1c-0',
            'channel-1::readline-6.2-0',
            'channel-1::sqlite-3.7.13-0',
            'channel-1::system-5.8-1',
            'channel-1::tk-8.5.13-0',
            'channel-1::zlib-1.2.7-0',
            'channel-1::python-2.7.5-0',
            'channel-1::numpy-1.6.2-py27_4',
            'channel-1::pytz-2013b-py27_0',
            'channel-1::six-1.3.0-py27_0',
            'channel-1::dateutil-2.1-py27_1',
            # 'channel-1::scipy-0.12.0-np16py27_p0', scipy is out here because it wasn't a requested spec
        )
        assert tuple(final_state_2) == tuple(solver._index[Dist(d)] for d in order)


def test_auto_update_conda():
    specs = MatchSpec("conda=1.3"),
    with get_solver(specs) as solver:
        final_state_1 = solver.solve_final_state()
        # PrefixDag(final_state_1, specs).open_url()
        print([Dist(rec).full_name for rec in final_state_1])
        order = (
            'channel-1::openssl-1.0.1c-0',
            'channel-1::readline-6.2-0',
            'channel-1::sqlite-3.7.13-0',
            'channel-1::system-5.8-1',
            'channel-1::tk-8.5.13-0',
            'channel-1::yaml-0.1.4-0',
            'channel-1::zlib-1.2.7-0',
            'channel-1::python-2.7.5-0',
            'channel-1::pyyaml-3.10-py27_0',
            'channel-1::conda-1.3.5-py27_0',
        )
        assert tuple(final_state_1) == tuple(solver._index[Dist(d)] for d in order)

    with env_vars({"CONDA_AUTO_UPDATE_CONDA": "yes"}, reset_context):
        specs_to_add = MatchSpec("pytz"),
        with get_solver(specs_to_add, prefix_records=final_state_1, history_specs=specs) as solver:
            final_state_2 = solver.solve_final_state()
            # PrefixDag(final_state_2, specs).open_url()
            print([Dist(rec).full_name for rec in final_state_2])
            order = (
                'channel-1::openssl-1.0.1c-0',
                'channel-1::readline-6.2-0',
                'channel-1::sqlite-3.7.13-0',
                'channel-1::system-5.8-1',
                'channel-1::tk-8.5.13-0',
                'channel-1::yaml-0.1.4-0',
                'channel-1::zlib-1.2.7-0',
                'channel-1::python-2.7.5-0',
                'channel-1::pytz-2013b-py27_0',
                'channel-1::pyyaml-3.10-py27_0',
                'channel-1::conda-1.3.5-py27_0',
            )
            assert tuple(final_state_2) == tuple(solver._index[Dist(d)] for d in order)

    with env_vars({"CONDA_AUTO_UPDATE_CONDA": "yes", "CONDA_ROOT_PREFIX": TEST_PREFIX}, reset_context):
        specs_to_add = MatchSpec("pytz"),
        with get_solver(specs_to_add, prefix_records=final_state_1, history_specs=specs) as solver:
            final_state_2 = solver.solve_final_state()
            # PrefixDag(final_state_2, specs).open_url()
            print([Dist(rec).full_name for rec in final_state_2])
            order = (
                'channel-1::openssl-1.0.1c-0',
                'channel-1::readline-6.2-0',
                'channel-1::sqlite-3.7.13-0',
                'channel-1::system-5.8-1',
                'channel-1::tk-8.5.13-0',
                'channel-1::yaml-0.1.4-0',
                'channel-1::zlib-1.2.7-0',
                'channel-1::python-2.7.5-0',
                'channel-1::pytz-2013b-py27_0',
                'channel-1::pyyaml-3.10-py27_0',
                'channel-1::conda-1.5.2-py27_0',
            )
            assert tuple(final_state_2) == tuple(solver._index[Dist(d)] for d in order)

    with env_vars({"CONDA_AUTO_UPDATE_CONDA": "no", "CONDA_ROOT_PREFIX": TEST_PREFIX}, reset_context):
        specs_to_add = MatchSpec("pytz"),
        with get_solver(specs_to_add, prefix_records=final_state_1, history_specs=specs) as solver:
            final_state_2 = solver.solve_final_state()
            # PrefixDag(final_state_2, specs).open_url()
            print([Dist(rec).full_name for rec in final_state_2])
            order = (
                'channel-1::openssl-1.0.1c-0',
                'channel-1::readline-6.2-0',
                'channel-1::sqlite-3.7.13-0',
                'channel-1::system-5.8-1',
                'channel-1::tk-8.5.13-0',
                'channel-1::yaml-0.1.4-0',
                'channel-1::zlib-1.2.7-0',
                'channel-1::python-2.7.5-0',
                'channel-1::pytz-2013b-py27_0',
                'channel-1::pyyaml-3.10-py27_0',
                'channel-1::conda-1.3.5-py27_0',
            )
            assert tuple(final_state_2) == tuple(solver._index[Dist(d)] for d in order)


def test_update_deps_1():
    specs = MatchSpec("python=2"),
    with get_solver(specs) as solver:
        final_state_1 = solver.solve_final_state()
        # PrefixDag(final_state_1, specs).open_url()
        # print([Dist(rec).full_name for rec in final_state_1])
        order = (
            'channel-1::openssl-1.0.1c-0',
            'channel-1::readline-6.2-0',
            'channel-1::sqlite-3.7.13-0',
            'channel-1::system-5.8-1',
            'channel-1::tk-8.5.13-0',
            'channel-1::zlib-1.2.7-0',
            'channel-1::python-2.7.5-0',
        )
        assert tuple(final_state_1) == tuple(solver._index[Dist(d)] for d in order)

    specs_to_add = MatchSpec("numpy=1.7.0"), MatchSpec("python=2.7.3")
    with get_solver(specs_to_add, prefix_records=final_state_1, history_specs=specs) as solver:
        final_state_2 = solver.solve_final_state()
        # PrefixDag(final_state_2, specs).open_url()
        print([Dist(rec).full_name for rec in final_state_2])
        order = (
            'channel-1::openssl-1.0.1c-0',
            'channel-1::readline-6.2-0',
            'channel-1::sqlite-3.7.13-0',
            'channel-1::system-5.8-1',
            'channel-1::tk-8.5.13-0',
            'channel-1::zlib-1.2.7-0',
            'channel-1::python-2.7.3-7',
            'channel-1::nose-1.3.0-py27_0',
            'channel-1::numpy-1.7.0-py27_0',
        )
        assert tuple(final_state_2) == tuple(solver._index[Dist(d)] for d in order)

    specs_to_add = MatchSpec("iopro"),
    with get_solver(specs_to_add, prefix_records=final_state_2, history_specs=specs) as solver:
        final_state_3 = solver.solve_final_state()
        # PrefixDag(final_state_2, specs).open_url()
        print([Dist(rec).full_name for rec in final_state_3])
        order = (
            'channel-1::openssl-1.0.1c-0',
            'channel-1::readline-6.2-0',
            'channel-1::sqlite-3.7.13-0',
            'channel-1::system-5.8-1',
            'channel-1::tk-8.5.13-0',
            'channel-1::unixodbc-2.3.1-0',
            'channel-1::zlib-1.2.7-0',
            'channel-1::python-2.7.3-7',
            'channel-1::nose-1.3.0-py27_0',
            'channel-1::numpy-1.7.0-py27_0',
            'channel-1::iopro-1.5.0-np17py27_p0',
        )
        assert tuple(final_state_3) == tuple(solver._index[Dist(d)] for d in order)

    specs_to_add = MatchSpec("iopro"),
    with get_solver(specs_to_add, prefix_records=final_state_2, history_specs=specs) as solver:
        final_state_3 = solver.solve_final_state(deps_modifier=DepsModifier.UPDATE_DEPS)
        # PrefixDag(final_state_2, specs).open_url()
        print([Dist(rec).full_name for rec in final_state_3])
        order = (
            'channel-1::openssl-1.0.1c-0',
            'channel-1::readline-6.2-0',
            'channel-1::sqlite-3.7.13-0',
            'channel-1::system-5.8-1',
            'channel-1::tk-8.5.13-0',
            'channel-1::unixodbc-2.3.1-0',
            'channel-1::zlib-1.2.7-0',
            'channel-1::python-2.7.5-0',   # with update_deps, numpy should switch from 1.7.0 to 1.7.1
            'channel-1::nose-1.3.0-py27_0',
            'channel-1::numpy-1.7.1-py27_0',  # with update_deps, numpy should switch from 1.7.0 to 1.7.1
            'channel-1::iopro-1.5.0-np17py27_p0',
        )
        assert tuple(final_state_3) == tuple(solver._index[Dist(d)] for d in order)

    specs_to_add = MatchSpec("iopro"),
    with get_solver(specs_to_add, prefix_records=final_state_2, history_specs=specs) as solver:
        final_state_3 = solver.solve_final_state(deps_modifier=DepsModifier.UPDATE_DEPS_ONLY_DEPS)
        # PrefixDag(final_state_2, specs).open_url()
        print([Dist(rec).full_name for rec in final_state_3])
        order = (
            'channel-1::openssl-1.0.1c-0',
            'channel-1::readline-6.2-0',
            'channel-1::sqlite-3.7.13-0',
            'channel-1::system-5.8-1',
            'channel-1::tk-8.5.13-0',
            'channel-1::unixodbc-2.3.1-0',
            'channel-1::zlib-1.2.7-0',
            'channel-1::python-2.7.5-0',   # with update_deps, numpy should switch from 1.7.0 to 1.7.1
            'channel-1::nose-1.3.0-py27_0',
            'channel-1::numpy-1.7.1-py27_0',  # with update_deps, numpy should switch from 1.7.0 to 1.7.1
            # 'channel-1::iopro-1.5.0-np17py27_p0',
        )
        assert tuple(final_state_3) == tuple(solver._index[Dist(d)] for d in order)


def test_pinned_1():
    specs = MatchSpec("numpy"),
    with get_solver(specs) as solver:
        final_state_1 = solver.solve_final_state()
        # PrefixDag(final_state_1, specs).open_url()
        print([Dist(rec).full_name for rec in final_state_1])
        order = (
            'channel-1::openssl-1.0.1c-0',
            'channel-1::readline-6.2-0',
            'channel-1::sqlite-3.7.13-0',
            'channel-1::system-5.8-1',
            'channel-1::tk-8.5.13-0',
            'channel-1::zlib-1.2.7-0',
            'channel-1::python-3.3.2-0',
            'channel-1::numpy-1.7.1-py33_0',
        )
        assert tuple(final_state_1) == tuple(solver._index[Dist(d)] for d in order)

    with env_var("CONDA_PINNED_PACKAGES", "python=2.6&iopro<=1.4.2", reset_context):
        specs = MatchSpec("system=5.8=0"),
        with get_solver(specs) as solver:
            final_state_1 = solver.solve_final_state()
            # PrefixDag(final_state_1, specs).open_url()
            print([Dist(rec).full_name for rec in final_state_1])
            order = (
                'channel-1::system-5.8-0',
            )
            assert tuple(final_state_1) == tuple(solver._index[Dist(d)] for d in order)

        specs_to_add = MatchSpec("python"),
        with get_solver(specs_to_add=specs_to_add, prefix_records=final_state_1,
                        history_specs=specs) as solver:
            final_state_2 = solver.solve_final_state(ignore_pinned=True)
            # PrefixDag(final_state_1, specs).open_url()
            print([Dist(rec).full_name for rec in final_state_2])
            order = (
                'channel-1::openssl-1.0.1c-0',
                'channel-1::readline-6.2-0',
                'channel-1::sqlite-3.7.13-0',
                'channel-1::system-5.8-0',
                'channel-1::tk-8.5.13-0',
                'channel-1::zlib-1.2.7-0',
                'channel-1::python-3.3.2-0',
            )
            assert tuple(final_state_2) == tuple(solver._index[Dist(d)] for d in order)

        specs_to_add = MatchSpec("python"),
        with get_solver(specs_to_add=specs_to_add, prefix_records=final_state_1,
                        history_specs=specs) as solver:
            final_state_2 = solver.solve_final_state()
            # PrefixDag(final_state_1, specs).open_url()
            print([Dist(rec).full_name for rec in final_state_2])
            order = (
                'channel-1::openssl-1.0.1c-0',
                'channel-1::readline-6.2-0',
                'channel-1::sqlite-3.7.13-0',
                'channel-1::system-5.8-0',
                'channel-1::tk-8.5.13-0',
                'channel-1::zlib-1.2.7-0',
                'channel-1::python-2.6.8-6',
            )
            assert tuple(final_state_2) == tuple(solver._index[Dist(d)] for d in order)

        specs_to_add = MatchSpec("numba"),
        history_specs = MatchSpec("python"), MatchSpec("system=5.8=0"),
        with get_solver(specs_to_add=specs_to_add, prefix_records=final_state_2,
                        history_specs=history_specs) as solver:
            final_state_3 = solver.solve_final_state()
            # PrefixDag(final_state_1, specs).open_url()
            print([Dist(rec).full_name for rec in final_state_3])
            order = (
                'channel-1::openssl-1.0.1c-0',
                'channel-1::readline-6.2-0',
                'channel-1::sqlite-3.7.13-0',
                'channel-1::system-5.8-0',
                'channel-1::tk-8.5.13-0',
                'channel-1::zlib-1.2.7-0',
                'channel-1::llvm-3.2-0',
                'channel-1::python-2.6.8-6',
                'channel-1::argparse-1.2.1-py26_0',
                'channel-1::llvmpy-0.11.2-py26_0',
                'channel-1::numpy-1.7.1-py26_0',
                'channel-1::numba-0.8.1-np17py26_0',
            )
            assert tuple(final_state_3) == tuple(solver._index[Dist(d)] for d in order)

        specs_to_add = MatchSpec("python"),
        history_specs = MatchSpec("python"), MatchSpec("system=5.8=0"), MatchSpec("numba"),
        with get_solver(specs_to_add=specs_to_add, prefix_records=final_state_3,
                        history_specs=history_specs) as solver:
            final_state_4 = solver.solve_final_state(deps_modifier=DepsModifier.UPDATE_DEPS)
            # PrefixDag(final_state_1, specs).open_url()
            print([Dist(rec).full_name for rec in final_state_4])
            order = (
                'channel-1::openssl-1.0.1c-0',
                'channel-1::readline-6.2-0',
                'channel-1::sqlite-3.7.13-0',
                'channel-1::system-5.8-1',
                'channel-1::tk-8.5.13-0',
                'channel-1::zlib-1.2.7-0',
                'channel-1::llvm-3.2-0',
                'channel-1::python-2.6.8-6',
                'channel-1::argparse-1.2.1-py26_0',
                'channel-1::llvmpy-0.11.2-py26_0',
                'channel-1::numpy-1.7.1-py26_0',
                'channel-1::numba-0.8.1-np17py26_0',
            )
            assert tuple(final_state_4) == tuple(solver._index[Dist(d)] for d in order)

        specs_to_add = MatchSpec("python"),
        history_specs = MatchSpec("python"), MatchSpec("system=5.8=0"), MatchSpec("numba"),
        with get_solver(specs_to_add=specs_to_add, prefix_records=final_state_4,
                        history_specs=history_specs) as solver:
            final_state_5 = solver.solve_final_state(deps_modifier=DepsModifier.UPDATE_ALL)
            # PrefixDag(final_state_1, specs).open_url()
            print([Dist(rec).full_name for rec in final_state_5])
            order = (
                'channel-1::openssl-1.0.1c-0',
                'channel-1::readline-6.2-0',
                'channel-1::sqlite-3.7.13-0',
                'channel-1::system-5.8-1',
                'channel-1::tk-8.5.13-0',
                'channel-1::zlib-1.2.7-0',
                'channel-1::llvm-3.2-0',
                'channel-1::python-2.6.8-6',
                'channel-1::argparse-1.2.1-py26_0',
                'channel-1::llvmpy-0.11.2-py26_0',
                'channel-1::numpy-1.7.1-py26_0',
                'channel-1::numba-0.8.1-np17py26_0',
            )
            assert tuple(final_state_5) == tuple(solver._index[Dist(d)] for d in order)

    # now update without pinning
    specs_to_add = MatchSpec("python"),
    history_specs = MatchSpec("python"), MatchSpec("system=5.8=0"), MatchSpec("numba"),
    with get_solver(specs_to_add=specs_to_add, prefix_records=final_state_4,
                    history_specs=history_specs) as solver:
        final_state_5 = solver.solve_final_state(deps_modifier=DepsModifier.UPDATE_ALL)
        # PrefixDag(final_state_1, specs).open_url()
        print([Dist(rec).full_name for rec in final_state_5])
        order = (
            'channel-1::openssl-1.0.1c-0',
            'channel-1::readline-6.2-0',
            'channel-1::sqlite-3.7.13-0',
            'channel-1::system-5.8-1',
            'channel-1::tk-8.5.13-0',
            'channel-1::zlib-1.2.7-0',
            'channel-1::llvm-3.2-0',
            'channel-1::python-3.3.2-0',
            'channel-1::llvmpy-0.11.2-py33_0',
            'channel-1::numpy-1.7.1-py33_0',
            'channel-1::numba-0.8.1-np17py33_0',
        )
        assert tuple(final_state_5) == tuple(solver._index[Dist(d)] for d in order)


def test_no_update_deps_1():  # i.e. FREEZE_DEPS
    # NOTE: So far, NOT actually testing the FREEZE_DEPS flag.  I'm unable to contrive a
    # situation where it's actually needed.

    specs = MatchSpec("python=2"),
    with get_solver(specs) as solver:
        final_state_1 = solver.solve_final_state()
        # PrefixDag(final_state_1, specs).open_url()
        print([Dist(rec).full_name for rec in final_state_1])
        order = (
            'channel-1::openssl-1.0.1c-0',
            'channel-1::readline-6.2-0',
            'channel-1::sqlite-3.7.13-0',
            'channel-1::system-5.8-1',
            'channel-1::tk-8.5.13-0',
            'channel-1::zlib-1.2.7-0',
            'channel-1::python-2.7.5-0',
        )
        assert tuple(final_state_1) == tuple(solver._index[Dist(d)] for d in order)

    specs_to_add = MatchSpec("zope.interface"),
    with get_solver(specs_to_add, prefix_records=final_state_1, history_specs=specs) as solver:
        final_state_2 = solver.solve_final_state()
        # PrefixDag(final_state_2, specs).open_url()
        print([Dist(rec).full_name for rec in final_state_2])
        order = (
            'channel-1::openssl-1.0.1c-0',
            'channel-1::readline-6.2-0',
            'channel-1::sqlite-3.7.13-0',
            'channel-1::system-5.8-1',
            'channel-1::tk-8.5.13-0',
            'channel-1::zlib-1.2.7-0',
            'channel-1::python-2.7.5-0',
            'channel-1::nose-1.3.0-py27_0',
            'channel-1::zope.interface-4.0.5-py27_0',
        )
        assert tuple(final_state_2) == tuple(solver._index[Dist(d)] for d in order)

    specs_to_add = MatchSpec("zope.interface>4.1"),
    with get_solver(specs_to_add, prefix_records=final_state_1, history_specs=specs) as solver:
        final_state_2 = solver.solve_final_state()
        # PrefixDag(final_state_2, specs).open_url()
        print([Dist(rec).full_name for rec in final_state_2])
        order = (
            'channel-1::openssl-1.0.1c-0',
            'channel-1::readline-6.2-0',
            'channel-1::sqlite-3.7.13-0',
            'channel-1::system-5.8-1',
            'channel-1::tk-8.5.13-0',
            'channel-1::zlib-1.2.7-0',
            'channel-1::python-3.3.2-0',
            'channel-1::nose-1.3.0-py33_0',
            'channel-1::zope.interface-4.1.1.1-py33_0',
        )
        assert tuple(final_state_2) == tuple(solver._index[Dist(d)] for d in order)


def test_force_reinstall_1():
    specs = MatchSpec("python=2"),
    with get_solver(specs) as solver:
        final_state_1 = solver.solve_final_state()
        # PrefixDag(final_state_1, specs).open_url()
        print([Dist(rec).full_name for rec in final_state_1])
        order = (
            'channel-1::openssl-1.0.1c-0',
            'channel-1::readline-6.2-0',
            'channel-1::sqlite-3.7.13-0',
            'channel-1::system-5.8-1',
            'channel-1::tk-8.5.13-0',
            'channel-1::zlib-1.2.7-0',
            'channel-1::python-2.7.5-0',
        )
        assert tuple(final_state_1) == tuple(solver._index[Dist(d)] for d in order)

    specs_to_add = specs
    with get_solver(specs_to_add, prefix_records=final_state_1, history_specs=specs) as solver:
        unlink_dists, link_dists = solver.solve_for_diff()
        assert not unlink_dists
        assert not link_dists

        unlink_dists, link_dists = solver.solve_for_diff(force_reinstall=True)
        assert len(unlink_dists) == len(link_dists) == 1
        assert unlink_dists[0] == link_dists[0]

        unlink_dists, link_dists = solver.solve_for_diff()
        assert not unlink_dists
        assert not link_dists


def test_force_reinstall_2():
    specs = MatchSpec("python=2"),
    with get_solver(specs) as solver:
        unlink_dists, link_dists = solver.solve_for_diff(force_reinstall=True)
        assert not unlink_dists
        # PrefixDag(final_state_1, specs).open_url()
        print([Dist(rec).full_name for rec in link_dists])
        order = (
            'channel-1::openssl-1.0.1c-0',
            'channel-1::readline-6.2-0',
            'channel-1::sqlite-3.7.13-0',
            'channel-1::system-5.8-1',
            'channel-1::tk-8.5.13-0',
            'channel-1::zlib-1.2.7-0',
            'channel-1::python-2.7.5-0',
        )
        assert tuple(link_dists) == tuple(solver._index[Dist(d)] for d in order)


def test_timestamps_1():
    specs = MatchSpec("python=3.6.2"),
    with get_solver_4(specs) as solver:
        unlink_dists, link_dists = solver.solve_for_diff(force_reinstall=True)
        assert not unlink_dists
        # PrefixDag(final_state_1, specs).open_url()
        print([Dist(rec).full_name for rec in link_dists])
        order = (
            'channel-4::ca-certificates-2017.08.26-h1d4fec5_0',
            'channel-4::libgcc-ng-7.2.0-h7cc24e2_2',
            'channel-4::libstdcxx-ng-7.2.0-h7a57d05_2',
            'channel-4::libffi-3.2.1-h4deb6c0_3',
            'channel-4::ncurses-6.0-h06874d7_1',
            'channel-4::openssl-1.0.2l-h077ae2c_5',
            'channel-4::tk-8.6.7-h5979e9b_1',
            'channel-4::xz-5.2.3-h2bcbf08_1',
            'channel-4::zlib-1.2.11-hfbfcf68_1',
            'channel-4::libedit-3.1-heed3624_0',
            'channel-4::readline-7.0-hac23ff0_3',
            'channel-4::sqlite-3.20.1-h6d8b0f3_1',
            'channel-4::python-3.6.2-hca45abc_19',  # this package has a later timestamp but lower hash value
                                                    # than the alternate 'channel-4::python-3.6.2-hda45abc_19'
        )
        assert tuple(link_dists) == tuple(solver._index[Dist(d)] for d in order)


def test_priority_1():
    specs = (MatchSpec("pandas"), MatchSpec("python=2.7"))
    with env_var("CONDA_CHANNEL_PRIORITY", "True", reset_context):
        with get_solver_aggregate_1(specs) as solver:
            final_state_1 = solver.solve_final_state()
            # PrefixDag(final_state_1, specs).open_url()
            print([Dist(rec).full_name for rec in final_state_1])
            order = (
                'channel-2::mkl-2017.0.1-0',
                'channel-2::openssl-1.0.2l-0',
                'channel-2::readline-6.2-2',
                'channel-2::sqlite-3.13.0-0',
                'channel-2::tk-8.5.18-0',
                'channel-2::zlib-1.2.8-3',
                'channel-2::python-2.7.13-0',
                'channel-2::numpy-1.13.0-py27_0',
                'channel-2::pytz-2017.2-py27_0',
                'channel-2::six-1.10.0-py27_0',
                'channel-2::python-dateutil-2.6.0-py27_0',
                'channel-2::pandas-0.20.2-np113py27_0',
            )
            assert tuple(final_state_1) == tuple(solver._index[Dist(d)] for d in order)

    with env_var("CONDA_CHANNEL_PRIORITY", "False", reset_context):
        with get_solver_aggregate_1(specs) as solver:
            final_state_1 = solver.solve_final_state()
            # PrefixDag(final_state_1, specs).open_url()
            print([Dist(rec).full_name for rec in final_state_1])
            order = (
                'channel-4::intel-openmp-2018.0.0-h15fc484_7',
                'channel-2::libffi-3.2.1-1',
                'channel-4::libgcc-ng-7.2.0-h7cc24e2_2',
                'channel-4::libstdcxx-ng-7.2.0-h7a57d05_2',
                'channel-2::openssl-1.0.2l-0',
                'channel-4::mkl-2018.0.0-hb491cac_4',
                'channel-4::ncurses-6.0-h06874d7_1',
                'channel-4::tk-8.6.7-h5979e9b_1',
                'channel-4::zlib-1.2.11-hfbfcf68_1',
                'channel-4::libedit-3.1-heed3624_0',
                'channel-4::readline-7.0-hac23ff0_3',
                'channel-4::sqlite-3.20.1-h6d8b0f3_1',
                'channel-4::python-2.7.14-hc2b0042_21',
                'channel-4::numpy-1.13.3-py27hbcc08e0_0',
                'channel-2::pytz-2017.2-py27_0',
                'channel-2::six-1.10.0-py27_0',
                'channel-4::python-dateutil-2.6.1-py27h4ca5741_1',
                'channel-4::pandas-0.20.3-py27h820b67f_2',
            )
            assert tuple(final_state_1) == tuple(solver._index[Dist(d)] for d in order)


def test_features_solve_1():
    # in this test, channel-2 is a view of pkgs/free/linux-64
    #   and channel-4 is a view of the newer pkgs/main/linux-64
    # The channel list, equivalent to context.channels is ('channel-2', 'channel-4')
    specs = (MatchSpec("python=2.7"), MatchSpec("numpy"), MatchSpec("nomkl"))
    with env_var("CONDA_CHANNEL_PRIORITY", "True", reset_context):
        with get_solver_aggregate_1(specs) as solver:
            final_state_1 = solver.solve_final_state()
            # PrefixDag(final_state_1, specs).open_url()
            print([Dist(rec).full_name for rec in final_state_1])
            order = (
                'channel-2::libgfortran-3.0.0-1',
                'channel-2::nomkl-1.0-0',
                'channel-2::openssl-1.0.2l-0',
                'channel-2::readline-6.2-2',
                'channel-2::sqlite-3.13.0-0',
                'channel-2::tk-8.5.18-0',
                'channel-2::zlib-1.2.8-3',
                'channel-2::openblas-0.2.19-0',
                'channel-2::python-2.7.13-0',
                'channel-2::numpy-1.13.0-py27_nomkl_0',
            )
            assert tuple(final_state_1) == tuple(solver._index[Dist(d)] for d in order)

    with env_var("CONDA_CHANNEL_PRIORITY", "False", reset_context):
        with get_solver_aggregate_1(specs) as solver:
            final_state_1 = solver.solve_final_state()
            # PrefixDag(final_state_1, specs).open_url()
            print([Dist(rec).full_name for rec in final_state_1])
            order = (
                'channel-4::intel-openmp-2018.0.0-h15fc484_7',
                'channel-2::libffi-3.2.1-1',
                'channel-4::libgcc-ng-7.2.0-h7cc24e2_2',
                'channel-4::libstdcxx-ng-7.2.0-h7a57d05_2',
                'channel-2::nomkl-1.0-0',
                'channel-2::openssl-1.0.2l-0',
                'channel-4::mkl-2018.0.0-hb491cac_4',  # <- this is wrong
                'channel-4::ncurses-6.0-h06874d7_1',
                'channel-4::tk-8.6.7-h5979e9b_1',
                'channel-4::zlib-1.2.11-hfbfcf68_1',
                'channel-4::libedit-3.1-heed3624_0',
                'channel-4::readline-7.0-hac23ff0_3',
                'channel-4::sqlite-3.20.1-h6d8b0f3_1',
                'channel-4::python-2.7.14-hc2b0042_21',
                'channel-4::numpy-1.13.3-py27hbcc08e0_0',
            )
            assert tuple(final_state_1) == tuple(solver._index[Dist(d)] for d in order)


@pytest.mark.integration  # this test is slower, so we'll lump it into integration
def test_freeze_deps_1(pytestconfig):

    # https://github.com/pytest-dev/pytest/issues/1599
    capmanager = pytestconfig.pluginmanager.getplugin('capturemanager')
    capmanager.suspendcapture()

    with stderr_log_level(TRACE, 'conda'):

        specs = MatchSpec("six=1.7"),
        with get_solver_2(specs) as solver:
            final_state_1 = solver.solve_final_state()
            # PrefixDag(final_state_1, specs).open_url()
            print([Dist(rec).full_name for rec in final_state_1])
            order = (
                'channel-2::openssl-1.0.2l-0',
                'channel-2::readline-6.2-2',
                'channel-2::sqlite-3.13.0-0',
                'channel-2::tk-8.5.18-0',
                'channel-2::xz-5.2.2-1',
                'channel-2::zlib-1.2.8-3',
                'channel-2::python-3.4.5-0',
                'channel-2::six-1.7.3-py34_0',
            )
            assert tuple(final_state_1) == tuple(solver._index[Dist(d)] for d in order)

        # to keep six=1.7 as a requested spec, we have to downgrade python to 2.7
        specs_to_add = MatchSpec("bokeh"),
        with get_solver_2(specs_to_add, prefix_records=final_state_1, history_specs=specs) as solver:
            final_state_2 = solver.solve_final_state()
            # PrefixDag(final_state_2, specs).open_url()
            print([Dist(rec).full_name for rec in final_state_2])
            order = (
                'channel-2::mkl-2017.0.1-0',
                'channel-2::openssl-1.0.2l-0',
                'channel-2::readline-6.2-2',
                'channel-2::sqlite-3.13.0-0',
                'channel-2::tk-8.5.18-0',
                'channel-2::xz-5.2.2-1',
                'channel-2::yaml-0.1.6-0',
                'channel-2::zlib-1.2.8-3',
                'channel-2::python-2.7.13-0',
                'channel-2::backports-1.0-py27_0',
                'channel-2::backports_abc-0.5-py27_0',
                'channel-2::futures-3.1.1-py27_0',
                'channel-2::markupsafe-0.23-py27_2',
                'channel-2::numpy-1.13.0-py27_0',
                'channel-2::pyyaml-3.12-py27_0',
                'channel-2::requests-2.14.2-py27_0',
                'channel-2::setuptools-27.2.0-py27_0',
                'channel-2::six-1.7.3-py27_0',
                'channel-2::bkcharts-0.2-py27_0',
                'channel-2::jinja2-2.9.6-py27_0',
                'channel-2::python-dateutil-2.6.0-py27_0',
                'channel-2::singledispatch-3.4.0.3-py27_0',
                'channel-2::ssl_match_hostname-3.4.0.2-py27_1',
                'channel-2::tornado-4.5.1-py27_0',
                'channel-2::bokeh-0.12.6-py27_0',
            )
            assert tuple(final_state_2) == tuple(solver._index[Dist(d)] for d in order)

        # now we can't install the latest bokeh 0.12.5, but instead we get bokeh 0.12.4
        specs_to_add = MatchSpec("bokeh"),
        with get_solver_2(specs_to_add, prefix_records=final_state_1,
                          history_specs=(MatchSpec("six=1.7"), MatchSpec("python=3.4"))) as solver:
            final_state_2 = solver.solve_final_state()
            # PrefixDag(final_state_2, specs).open_url()
            print([Dist(rec).full_name for rec in final_state_2])
            order = (
                'channel-2::mkl-2017.0.1-0',
                'channel-2::openssl-1.0.2l-0',
                'channel-2::readline-6.2-2',
                'channel-2::sqlite-3.13.0-0',
                'channel-2::tk-8.5.18-0',
                'channel-2::xz-5.2.2-1',
                'channel-2::yaml-0.1.6-0',
                'channel-2::zlib-1.2.8-3',
                'channel-2::python-3.4.5-0',
                'channel-2::backports_abc-0.5-py34_0',
                'channel-2::markupsafe-0.23-py34_2',
                'channel-2::numpy-1.13.0-py34_0',
                'channel-2::pyyaml-3.12-py34_0',
                'channel-2::requests-2.14.2-py34_0',
                'channel-2::setuptools-27.2.0-py34_0',
                'channel-2::six-1.7.3-py34_0',
                'channel-2::jinja2-2.9.6-py34_0',
                'channel-2::python-dateutil-2.6.0-py34_0',
                'channel-2::tornado-4.4.2-py34_0',
                'channel-2::bokeh-0.12.4-py34_0',
            )
            assert tuple(final_state_2) == tuple(solver._index[Dist(d)] for d in order)

        # here, the python=3.4 spec can't be satisfied, so it's dropped, and we go back to py27
        specs_to_add = MatchSpec("bokeh=0.12.5"),
        with get_solver_2(specs_to_add, prefix_records=final_state_1,
                          history_specs=(MatchSpec("six=1.7"), MatchSpec("python=3.4"))) as solver:
            final_state_2 = solver.solve_final_state()
            # PrefixDag(final_state_2, specs).open_url()
            print([Dist(rec).full_name for rec in final_state_2])
            order = (
                'channel-2::mkl-2017.0.1-0',
                'channel-2::openssl-1.0.2l-0',
                'channel-2::readline-6.2-2',
                'channel-2::sqlite-3.13.0-0',
                'channel-2::tk-8.5.18-0',
                'channel-2::xz-5.2.2-1',
                'channel-2::yaml-0.1.6-0',
                'channel-2::zlib-1.2.8-3',
                'channel-2::python-2.7.13-0',
                'channel-2::backports-1.0-py27_0',
                'channel-2::backports_abc-0.5-py27_0',
                'channel-2::futures-3.1.1-py27_0',
                'channel-2::markupsafe-0.23-py27_2',
                'channel-2::numpy-1.13.0-py27_0',
                'channel-2::pyyaml-3.12-py27_0',
                'channel-2::requests-2.14.2-py27_0',
                'channel-2::setuptools-27.2.0-py27_0',
                'channel-2::six-1.7.3-py27_0',
                'channel-2::jinja2-2.9.6-py27_0',
                'channel-2::python-dateutil-2.6.0-py27_0',
                'channel-2::singledispatch-3.4.0.3-py27_0',
                'channel-2::ssl_match_hostname-3.4.0.2-py27_1',
                'channel-2::tornado-4.5.1-py27_0',
                'channel-2::bokeh-0.12.5-py27_1',
            )
            assert tuple(final_state_2) == tuple(solver._index[Dist(d)] for d in order)

        # here, the python=3.4 spec can't be satisfied, so it's dropped, and we go back to py27
        specs_to_add = MatchSpec("bokeh=0.12.5"),
        with get_solver_2(specs_to_add, prefix_records=final_state_1,
                          history_specs=(MatchSpec("six=1.7"), MatchSpec("python=3.4"))) as solver:
            with pytest.raises(UnsatisfiableError):
                solver.solve_final_state(deps_modifier=DepsModifier.FREEZE_INSTALLED)

    capmanager.resumecapture()


class PrivateEnvTests(TestCase):

    def setUp(self):
        self.prefix = '/a/test/c/prefix'

        self.preferred_env = "_spiffy-test-app_"
        self.preferred_env_prefix = join(self.prefix, 'envs', self.preferred_env)

        # self.save_path_conflict = os.environ.get('CONDA_PATH_CONFLICT')
        self.saved_values = {}
        self.saved_values['CONDA_ROOT_PREFIX'] = os.environ.get('CONDA_ROOT_PREFIX')
        self.saved_values['CONDA_ENABLE_PRIVATE_ENVS'] = os.environ.get('CONDA_ENABLE_PRIVATE_ENVS')

        # os.environ['CONDA_PATH_CONFLICT'] = 'prevent'
        os.environ['CONDA_ROOT_PREFIX'] = self.prefix
        os.environ['CONDA_ENABLE_PRIVATE_ENVS'] = 'true'

        reset_context()

    def tearDown(self):
        for key, value in iteritems(self.saved_values):
            if value is not None:
                os.environ[key] = value
            else:
                del os.environ[key]

        reset_context()

    # @patch.object(Context, 'prefix_specified')
    # def test_simple_install_uninstall(self, prefix_specified):
    #     prefix_specified.__get__ = Mock(return_value=False)
    #
    #     specs = MatchSpec("spiffy-test-app"),
    #     with get_solver_3(specs) as solver:
    #         final_state_1 = solver.solve_final_state()
    #         # PrefixDag(final_state_1, specs).open_url()
    #         print([Dist(rec).full_name for rec in final_state_1])
    #         order = (
    #             'channel-1::openssl-1.0.2l-0',
    #             'channel-1::readline-6.2-2',
    #             'channel-1::sqlite-3.13.0-0',
    #             'channel-1::tk-8.5.18-0',
    #             'channel-1::zlib-1.2.8-3',
    #             'channel-1::python-2.7.13-0',
    #             'channel-1::spiffy-test-app-2.0-py27hf99fac9_0',
    #         )
    #         assert tuple(final_state_1) == tuple(solver._index[Dist(d)] for d in order)
    #
    #     specs_to_add = MatchSpec("uses-spiffy-test-app"),
    #     with get_solver_3(specs_to_add, prefix_records=final_state_1, history_specs=specs) as solver:
    #         final_state_2 = solver.solve_final_state()
    #         # PrefixDag(final_state_2, specs).open_url()
    #         print([Dist(rec).full_name for rec in final_state_2])
    #         order = (
    #
    #         )
    #         assert tuple(final_state_2) == tuple(solver._index[Dist(d)] for d in order)
    #
    #     specs = specs + specs_to_add
    #     specs_to_remove = MatchSpec("uses-spiffy-test-app"),
    #     with get_solver_3(specs_to_remove=specs_to_remove, prefix_records=final_state_2,
    #                       history_specs=specs) as solver:
    #         final_state_3 = solver.solve_final_state()
    #         # PrefixDag(final_state_2, specs).open_url()
    #         print([Dist(rec).full_name for rec in final_state_3])
    #         order = (
    #
    #         )
    #         assert tuple(final_state_3) == tuple(solver._index[Dist(d)] for d in order)
