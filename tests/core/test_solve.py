# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from collections import defaultdict

from conda.core.index import _supplement_index_with_prefix
from conda.core.linked_data import PrefixData
from conda.history import History
from conda.models.dag import SimpleDag
from conda.models.dist import Dist

from conda.base.context import context
from conda.core.solve import Solver, DepsModifier
from conda.models.channel import Channel
from conda.models.prefix_record import PrefixRecord
from conda.resolve import MatchSpec
from ..helpers import index, r, patch

prefix = '/a/test/c/prefix'


def test_1():
    PrefixData._cache_ = {}
    specs = MatchSpec("numpy"),
    solver = Solver(prefix, (Channel('defaults'),), context.subdirs, specs_to_add=specs)
    solver.index = index
    solver.r = r
    solver._prepared = True
    final_state = solver.solve_final_state()

    order = (
        'defaults::openssl-1.0.1c-0',
        'defaults::readline-6.2-0',
        'defaults::sqlite-3.7.13-0',
        'defaults::system-5.8-1',
        'defaults::tk-8.5.13-0',
        'defaults::zlib-1.2.7-0',
        'defaults::python-3.3.2-0',
        'defaults::numpy-1.7.1-py33_0',
    )
    assert tuple(final_state) == tuple(index[Dist(d)] for d in order)

    PrefixData._cache_ = {}
    pd = PrefixData(prefix)
    pd._PrefixData__prefix_records = {rec.name: PrefixRecord.from_objects(rec) for rec in final_state}
    spec_map = {spec.name: spec for spec in specs}
    with patch.object(History, 'get_requested_specs_map', return_value=spec_map):
        solver = Solver(prefix, (Channel('defaults'),), context.subdirs, specs_to_add=(MatchSpec("python=2"),))
        solver.index = index
        solver.r = r
        solver._prepared = True

        final_state = solver.solve_final_state()

        print([Dist(rec).full_name for rec in final_state])

        order = (
            'defaults::openssl-1.0.1c-0',
            'defaults::readline-6.2-0',
            'defaults::sqlite-3.7.13-0',
            'defaults::system-5.8-1',
            'defaults::tk-8.5.13-0',
            'defaults::zlib-1.2.7-0',
            'defaults::python-2.7.5-0',
            'defaults::numpy-1.7.1-py27_0',
        )
        assert tuple(final_state) == tuple(index[Dist(d)] for d in order)



def test_prune_2():
    PrefixData._cache_ = {}
    solver = Solver(prefix, (Channel('defaults'),), context.subdirs, specs_to_remove=(MatchSpec("python=2"),))
    solver.index = index
    solver.r = r
    solver._prepared = True

    spec_map = {'sqlite': MatchSpec("sqlite=3")}
    with patch.object(History, 'get_requested_specs_map', return_value=spec_map):
        final_state = solver.solve_final_state(prune=True)
        print(final_state)
        assert len(final_state) == 1



def test_prune_1():
    PrefixData._cache_ = {}

    specs = (
        MatchSpec("numpy=1.6"), MatchSpec("python=2.7.3"), MatchSpec("accelerate"),
    )

    solver = Solver(prefix, (Channel('defaults'),), context.subdirs, specs_to_add=specs)
    solver.index = index
    solver.r = r
    solver._prepared = True
    final_state_1 = solver.solve_final_state()

    # SimpleDag(final_state_1, specs).open_url()
    # print([Dist(rec).full_name for rec in final_state_1])

    order = (
        'defaults::libnvvm-1.0-p0',
        'defaults::openssl-1.0.1c-0',
        'defaults::readline-6.2-0',
        'defaults::sqlite-3.7.13-0',
        'defaults::system-5.8-1',
        'defaults::tk-8.5.13-0',
        'defaults::zlib-1.2.7-0',
        'defaults::llvm-3.2-0',
        'defaults::mkl-rt-11.0-p0',
        'defaults::python-2.7.3-7',
        'defaults::bitarray-0.8.1-py27_0',
        'defaults::llvmpy-0.11.2-py27_0',
        'defaults::meta-0.4.2.dev-py27_0',
        'defaults::mkl-service-1.0.0-py27_p0',
        'defaults::numpy-1.6.2-py27_p4',
        'defaults::numba-0.8.1-np16py27_0',
        'defaults::numexpr-2.1-np16py27_p0',
        'defaults::scipy-0.12.0-np16py27_p0',
        'defaults::numbapro-0.11.0-np16py27_p0',
        'defaults::scikit-learn-0.13.1-np16py27_p0',
        'defaults::mkl-11.0-np16py27_p0',
        'defaults::accelerate-1.1.0-np16py27_p0',
    )
    assert tuple(final_state_1) == tuple(index[Dist(d)] for d in order)

    PrefixData._cache_ = {}
    pd = PrefixData(prefix)
    pd._PrefixData__prefix_records = {rec.name: PrefixRecord.from_objects(rec) for rec in final_state_1}
    spec_map = {spec.name: spec for spec in specs}
    with patch.object(History, 'get_requested_specs_map', return_value=spec_map):
        solver = Solver(prefix, (Channel('defaults'),), context.subdirs, specs_to_remove=(MatchSpec("numbapro"),))
        solver.index = index
        solver.r = r
        solver._prepared = True

        final_state_2 = solver.solve_final_state(prune=False)
        # SimpleDag(final_state_2, specs).open_url()
        print([Dist(rec).full_name for rec in final_state_2])
        order = (
            'defaults::libnvvm-1.0-p0',
            'defaults::openssl-1.0.1c-0',
            'defaults::readline-6.2-0',
            'defaults::sqlite-3.7.13-0',
            'defaults::system-5.8-1',
            'defaults::tk-8.5.13-0',
            'defaults::zlib-1.2.7-0',
            'defaults::llvm-3.2-0',
            'defaults::mkl-rt-11.0-p0',
            'defaults::python-2.7.3-7',
            'defaults::bitarray-0.8.1-py27_0',
            'defaults::llvmpy-0.11.2-py27_0',
            'defaults::meta-0.4.2.dev-py27_0',
            'defaults::mkl-service-1.0.0-py27_p0',
            'defaults::numpy-1.6.2-py27_p4',
            'defaults::numba-0.8.1-np16py27_0',
            'defaults::numexpr-2.1-np16py27_p0',
            'defaults::scipy-0.12.0-np16py27_p0',
            'defaults::scikit-learn-0.13.1-np16py27_p0',
            'defaults::mkl-11.0-np16py27_p0',
        )
        assert tuple(final_state_2) == tuple(index[Dist(d)] for d in order)

        solver = Solver(prefix, (Channel('defaults'),), context.subdirs, specs_to_remove=(MatchSpec("numbapro"),))
        solver.index = index
        solver.r = r
        solver._prepared = True

        final_state_2 = solver.solve_final_state(prune=True)
        # SimpleDag(final_state_2, specs).open_url()
        print([Dist(rec).full_name for rec in final_state_2])
        order = (
            'defaults::openssl-1.0.1c-0',
            'defaults::readline-6.2-0',
            'defaults::sqlite-3.7.13-0',
            'defaults::system-5.8-1',
            'defaults::tk-8.5.13-0',
            'defaults::zlib-1.2.7-0',
            'defaults::python-2.7.3-7',
            'defaults::numpy-1.6.2-py27_4',
        )
        assert tuple(final_state_2) == tuple(index[Dist(d)] for d in order)








def test_no_deps_1():
    PrefixData._cache_ = {}
    specs = MatchSpec("python=2"),
    solver = Solver(prefix, (Channel('defaults'),), context.subdirs, specs_to_add=specs)
    solver.index = index
    solver.r = r
    solver._prepared = True
    final_state_1 = solver.solve_final_state()

    # SimpleDag(final_state_1, specs).open_url()
    # print([Dist(rec).full_name for rec in final_state_1])

    order = (
        'defaults::openssl-1.0.1c-0',
        'defaults::readline-6.2-0',
        'defaults::sqlite-3.7.13-0',
        'defaults::system-5.8-1',
        'defaults::tk-8.5.13-0',
        'defaults::zlib-1.2.7-0',
        'defaults::python-2.7.5-0',
    )
    assert tuple(final_state_1) == tuple(index[Dist(d)] for d in order)

    PrefixData._cache_ = {}
    pd = PrefixData(prefix)
    pd._PrefixData__prefix_records = {rec.name: PrefixRecord.from_objects(rec) for rec in final_state_1}
    spec_map = {spec.name: spec for spec in specs}
    with patch.object(History, 'get_requested_specs_map', return_value=spec_map):
        solver = Solver(prefix, (Channel('defaults'),), context.subdirs, specs_to_add=(MatchSpec("numba"),))
        solver.index = index
        solver.r = r
        solver._prepared = True

        final_state_2 = solver.solve_final_state()
        # SimpleDag(final_state_2, specs).open_url()
        print([Dist(rec).full_name for rec in final_state_2])
        order = (
            'defaults::openssl-1.0.1c-0',
            'defaults::readline-6.2-0',
            'defaults::sqlite-3.7.13-0',
            'defaults::system-5.8-1',
            'defaults::tk-8.5.13-0',
            'defaults::zlib-1.2.7-0',
            'defaults::llvm-3.2-0',
            'defaults::python-2.7.5-0',
            'defaults::llvmpy-0.11.2-py27_0',
            'defaults::meta-0.4.2.dev-py27_0',
            'defaults::numpy-1.7.1-py27_0',
            'defaults::numba-0.8.1-np17py27_0'
        )
        assert tuple(final_state_2) == tuple(index[Dist(d)] for d in order)

    PrefixData._cache_ = {}
    pd = PrefixData(prefix)
    pd._PrefixData__prefix_records = {rec.name: PrefixRecord.from_objects(rec) for rec in final_state_1}
    spec_map = {spec.name: spec for spec in specs}
    with patch.object(History, 'get_requested_specs_map', return_value=spec_map):
        solver = Solver(prefix, (Channel('defaults'),), context.subdirs, specs_to_add=(MatchSpec("numba"),))
        solver.index = index
        solver.r = r
        solver._prepared = True

        final_state_2 = solver.solve_final_state(deps_modifier=DepsModifier.NO_DEPS)
        # SimpleDag(final_state_2, specs).open_url()
        print([Dist(rec).full_name for rec in final_state_2])
        order = (
            'defaults::openssl-1.0.1c-0',
            'defaults::readline-6.2-0',
            'defaults::sqlite-3.7.13-0',
            'defaults::system-5.8-1',
            'defaults::tk-8.5.13-0',
            'defaults::zlib-1.2.7-0',
            'defaults::python-2.7.5-0',
            'defaults::numba-0.8.1-np17py27_0',
        )
        assert tuple(final_state_2) == tuple(index[Dist(d)] for d in order)


def test_only_deps_1():
    PrefixData._cache_ = {}
    specs = MatchSpec("numba[build=*py27*]"),
    solver = Solver(prefix, (Channel('defaults'),), context.subdirs, specs_to_add=specs)
    solver.index = index
    solver.r = r
    solver._prepared = True
    final_state_1 = solver.solve_final_state(deps_modifier=DepsModifier.ONLY_DEPS)

    # SimpleDag(final_state_1, specs).open_url()
    # print([Dist(rec).full_name for rec in final_state_1])

    order = (
        'defaults::openssl-1.0.1c-0',
        'defaults::readline-6.2-0',
        'defaults::sqlite-3.7.13-0',
        'defaults::system-5.8-1',
        'defaults::tk-8.5.13-0',
        'defaults::zlib-1.2.7-0',
        'defaults::llvm-3.2-0',
        'defaults::python-2.7.5-0',
        'defaults::llvmpy-0.11.2-py27_0',
        'defaults::meta-0.4.2.dev-py27_0',
        'defaults::numpy-1.7.1-py27_0',
    )
    assert tuple(final_state_1) == tuple(index[Dist(d)] for d in order)



def test_only_deps_2():
    PrefixData._cache_ = {}
    specs = MatchSpec("numpy=1.5"), MatchSpec("python=2.7.3"),
    solver = Solver(prefix, (Channel('defaults'),), context.subdirs, specs_to_add=specs)
    solver.index = index
    solver.r = r
    solver._prepared = True
    final_state_1 = solver.solve_final_state()

    # SimpleDag(final_state_1, specs).open_url()
    print([Dist(rec).full_name for rec in final_state_1])

    order = (
        'defaults::openssl-1.0.1c-0',
        'defaults::readline-6.2-0',
        'defaults::sqlite-3.7.13-0',
        'defaults::system-5.8-1',
        'defaults::tk-8.5.13-0',
        'defaults::zlib-1.2.7-0',
        'defaults::python-2.7.3-7',
        'defaults::numpy-1.5.1-py27_4',
    )

    assert tuple(final_state_1) == tuple(index[Dist(d)] for d in order)

    # TODO:
    # PrefixData._cache_ = {}
    # pd = PrefixData(prefix)
    # pd._PrefixData__prefix_records = {rec.name: PrefixRecord.from_objects(rec) for rec in final_state_1}
    # spec_map = {spec.name: spec for spec in specs}
    # with patch.object(History, 'get_requested_specs_map', return_value=spec_map):
    #     solver = Solver(prefix, (Channel('defaults'),), context.subdirs,
    #                     specs_to_add=(MatchSpec("numba=0.5"),))
    #     solver.index = index
    #     solver.r = r
    #     solver._prepared = True
    #
    #     final_state_2 = solver.solve_final_state(deps_modifier=DepsModifier.ONLY_DEPS)
    #     # SimpleDag(final_state_2, specs).open_url()
    #     print([Dist(rec).full_name for rec in final_state_2])
    #
    #     order = (
    #         'defaults::openssl-1.0.1c-0',
    #         'defaults::readline-6.2-0',
    #         'defaults::sqlite-3.7.13-0',
    #         'defaults::system-5.8-1',
    #         'defaults::tk-8.5.13-0',
    #         'defaults::zlib-1.2.7-0',
    #         'defaults::llvm-3.1-1',
    #         'defaults::python-2.7.3-7',
    #         'defaults::llvmpy-0.8.3-py27_0',
    #         'defaults::meta-0.4.2.dev-py27_0',
    #         'defaults::nose-1.3.0-py27_0',
    #         'defaults::numpy-1.5.1-py27_4',
    #     )
    #     assert tuple(final_state_2) == tuple(index[Dist(d)] for d in order)


def test_update_all_1():
    PrefixData._cache_ = {}
    specs = MatchSpec("numpy=1.5"), MatchSpec("python=2.6"), MatchSpec("system[build_number=0]")
    solver = Solver(prefix, (Channel('defaults'),), context.subdirs, specs_to_add=specs)
    solver.index = index
    solver.r = r
    solver._prepared = True
    final_state_1 = solver.solve_final_state()

    # SimpleDag(final_state_1, specs).open_url()
    print([Dist(rec).full_name for rec in final_state_1])

    order = (
        'defaults::openssl-1.0.1c-0',
        'defaults::readline-6.2-0',
        'defaults::sqlite-3.7.13-0',
        'defaults::system-5.8-0',
        'defaults::tk-8.5.13-0',
        'defaults::zlib-1.2.7-0',
        'defaults::python-2.6.8-6',
        'defaults::numpy-1.5.1-py26_4',
    )

    assert tuple(final_state_1) == tuple(index[Dist(d)] for d in order)


    PrefixData._cache_ = {}
    pd = PrefixData(prefix)
    pd._PrefixData__prefix_records = {rec.name: PrefixRecord.from_objects(rec) for rec in final_state_1}
    spec_map = {spec.name: spec for spec in specs}
    with patch.object(History, 'get_requested_specs_map', return_value=spec_map):
        solver = Solver(prefix, (Channel('defaults'),), context.subdirs,
                        specs_to_add=(MatchSpec("numba=0.6"), MatchSpec("numpy")))
        solver.index = index
        solver.r = r
        solver._prepared = True

        final_state_2 = solver.solve_final_state()
        # SimpleDag(final_state_2, specs).open_url()
        print([Dist(rec).full_name for rec in final_state_2])

        order = (
            'defaults::openssl-1.0.1c-0',
            'defaults::readline-6.2-0',
            'defaults::sqlite-3.7.13-0',
            'defaults::system-5.8-0',
            'defaults::tk-8.5.13-0',
            'defaults::zlib-1.2.7-0',
            'defaults::llvm-3.2-0',
            'defaults::python-2.6.8-6',
            'defaults::llvmpy-0.10.2-py26_0',
            'defaults::nose-1.3.0-py26_0',
            'defaults::numpy-1.7.1-py26_0',
            'defaults::numba-0.6.0-np17py26_0',
        )
        assert tuple(final_state_2) == tuple(index[Dist(d)] for d in order)


    PrefixData._cache_ = {}
    pd = PrefixData(prefix)
    pd._PrefixData__prefix_records = {rec.name: PrefixRecord.from_objects(rec) for rec in final_state_1}
    spec_map = {spec.name: spec for spec in specs}
    with patch.object(History, 'get_requested_specs_map', return_value=spec_map):
        solver = Solver(prefix, (Channel('defaults'),), context.subdirs,
                        specs_to_add=(MatchSpec("numba=0.6"),))
        solver.index = index
        solver.r = r
        solver._prepared = True

        final_state_2 = solver.solve_final_state(deps_modifier=DepsModifier.UPDATE_ALL)
        # SimpleDag(final_state_2, specs).open_url()
        print([Dist(rec).full_name for rec in final_state_2])

        order = (
            'defaults::openssl-1.0.1c-0',
            'defaults::readline-6.2-0',
            'defaults::sqlite-3.7.13-0',
            'defaults::system-5.8-1',
            'defaults::tk-8.5.13-0',
            'defaults::zlib-1.2.7-0',
            'defaults::llvm-3.2-0',
            'defaults::python-2.7.5-0',
            'defaults::llvmpy-0.10.2-py27_0',
            'defaults::meta-0.4.2.dev-py27_0',
            'defaults::nose-1.3.0-py27_0',
            'defaults::numpy-1.7.1-py27_0',
            'defaults::numba-0.6.0-np17py27_0'
        )
        assert tuple(final_state_2) == tuple(index[Dist(d)] for d in order)

