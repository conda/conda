# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from logging import getLogger

from conda.models.dag import PrefixDag
from conda.models.match_spec import MatchSpec
from tests.core.test_solve import get_solver_2

log = getLogger(__name__)


def test_ordered_nodes():
    specs = MatchSpec("numpy"),

    with get_solver_2(specs) as solver:
        final_state = solver.solve_final_state()
        dag = PrefixDag(final_state, specs)
        # dag.open_url()
        from_roots = dag.get_nodes_ordered_from_roots()
        from_roots_order = (
            'mkl',
            'openssl',
            'readline',
            'sqlite',
            'tk',
            'xz',
            'zlib',
            'python',
            'numpy',
        )
        assert tuple(n.record.name for n in from_roots) == from_roots_order
        from_leaves = dag.get_nodes_ordered_from_leaves()
        assert tuple(n.record.name for n in from_leaves) == (
            'numpy',
            'mkl',
            'python',
            'openssl',
            'readline',
            'sqlite',
            'tk',
            'xz',
            'zlib',
        )

        leaves_last = dag.order_nodes_from_roots(from_roots)
        assert leaves_last == dag.order_nodes_from_roots(from_leaves)
        assert tuple(n.record.name for n in leaves_last) == from_roots_order


def test_remove_node_and_children():
    specs = MatchSpec("pandas"),
    with get_solver_2(specs) as solver:
        final_state = solver.solve_final_state()

        dag = PrefixDag(final_state, specs)
        six_node = next((n for n in dag.nodes if n.record.name == 'six'))
        assert set(n.record.name for n in six_node.all_descendants()) == {
            'pandas',
            'python-dateutil',
        }
        assert set(n.record.name for n in six_node.all_ascendants()) == {
            'openssl',
            'readline',
            'sqlite',
            'tk',
            'xz',
            'zlib',
            'python',
        }
        removed_records = tuple(dag.remove_node_and_children(six_node))
        assert tuple(r.name for r in removed_records) == (
            'pandas',
            'python-dateutil',
            'six',
        )

        dag = PrefixDag(final_state, specs)
        python_node = next((n for n in dag.nodes if n.record.name == 'python'))
        assert set(n.record.name for n in python_node.all_descendants()) == {
            'pandas',
            'pytz',
            'numpy',
            'six',
            'python-dateutil',
        }
        assert set(n.record.name for n in python_node.all_ascendants()) == {
            'openssl',
            'readline',
            'sqlite',
            'tk',
            'xz',
            'zlib',
        }
        removed_records = tuple(dag.remove_node_and_children(python_node))
        assert tuple(r.name for r in removed_records) == (
            'pandas',
            'numpy',
            'pytz',
            'python-dateutil',
            'six',
            'python',
        )
