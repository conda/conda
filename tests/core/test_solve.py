# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from collections import defaultdict

from conda.core.index import _supplement_index_with_prefix
from conda.core.linked_data import PrefixData
from conda.history import History
from conda.models.dag import SimpleDag
from conda.models.dist import Dist

from conda.base.context import context
from conda.core.solve import Solver
from conda.models.channel import Channel
from conda.models.prefix_record import PrefixRecord
from conda.resolve import MatchSpec
from ..helpers import index, r, patch

prefix = '/a/test/c/prefix'


def test_1():
    solver = Solver(prefix, (Channel('defaults'),), context.subdirs, (MatchSpec("numpy"),))
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


    pd = PrefixData(prefix)
    pd._PrefixData__prefix_records = {rec.name: PrefixRecord.from_objects(rec) for rec in final_state}

    solver = Solver(prefix, (Channel('defaults'),), context.subdirs, (MatchSpec("python=2"),))
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
        'defaults::python-2.7.5-0',
        'defaults::numpy-1.7.1-py27_0',
    )
    assert tuple(final_state) == tuple(index[Dist(d)] for d in order)


def test_3():
    solver = Solver(prefix, (Channel('defaults'),), context.subdirs, specs_to_remove=(MatchSpec("python=2"),))
    solver.index = index
    solver.r = r
    solver._prepared = True

    # final_state = solver.solve_final_state()
    # order = (
    #     'defaults::openssl-1.0.1c-0',
    #     'defaults::readline-6.2-0',
    #     'defaults::sqlite-3.7.13-0',
    #     'defaults::system-5.8-1',
    #     'defaults::tk-8.5.13-0',
    #     'defaults::zlib-1.2.7-0',
    # )
    # assert tuple(final_state) == tuple(index[Dist(d)] for d in order)
    #
    # final_state = solver.solve_final_state(prune=True)
    # assert len(final_state) == 0

    spec_map = {'sqlite': MatchSpec("sqlite=3")}
    with patch.object(History, 'get_requested_specs_map', return_value=spec_map):
        final_state = solver.solve_final_state(prune=True)
        assert len(final_state) == 3







def test_prune():

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

    spec_map = {spec.name: spec for spec in specs}
    with patch.object(History, 'get_requested_specs_map', return_value=spec_map):
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
            'defaults::mkl-rt-11.0-p0',
            'defaults::python-2.7.3-7',
            'defaults::numpy-1.6.2-py27_p4',
        )
        assert tuple(final_state_2) == tuple(index[Dist(d)] for d in order)







