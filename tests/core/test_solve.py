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
    solver = Solver(prefix, (Channel('defaults'),), context.subdirs, specs_to_remove=(MatchSpec("python"),))
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
    )
    assert tuple(final_state) == tuple(index[Dist(d)] for d in order)

    final_state = solver.solve_final_state(prune=True)
    assert len(final_state) == 0

    spec_map = {'sqlite': MatchSpec("sqlite=3")}
    with patch.object(History, 'get_requested_specs_map', return_value=spec_map):
        final_state = solver.solve_final_state(prune=True)
        assert len(final_state) == 3







def test_4():

    specs = (
        MatchSpec("flask"), MatchSpec("pandas"), MatchSpec("accelerate"), MatchSpec("numpy=1.6"),
    )

    solver = Solver(prefix, (Channel('defaults'),), context.subdirs, specs_to_add=specs)
    solver.index = index
    solver.r = r
    solver._prepared = True
    final_state = solver.solve_final_state()

    dag = SimpleDag(final_state, specs)









