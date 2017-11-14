# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import inspect

from conda.api import Solver
from conda.common.compat import odict
from conda.common.constants import NULL


def inspect_arguments(f, arguments):
    result = inspect.getargspec(f)
    arg_names = result[0]
    default_val_first_idx = len(arg_names) - len(result.defaults)
    arg_values = [NULL] * default_val_first_idx + list(result.defaults)
    for (recorded_name, recorded_value), (arg_name, arg_value) in zip(arguments.items(), zip(arg_names, arg_values)):
        print(recorded_name, arg_name)
        assert recorded_name == arg_name
        assert recorded_value == arg_value


def test_Solver_contract():
    init_args = odict((
        ('self', NULL),
        ('prefix', NULL),
        ('channels', NULL),
        ('subdirs', ()),
        ('specs_to_add', ()),
        ('specs_to_remove', ()),
    ))
    inspect_arguments(Solver.__init__, init_args)

    solve_final_state_args = odict((
        ('self', NULL),
        ('deps_modifier', NULL),
        ('prune', NULL),
        ('ignore_pinned', NULL),
        ('force_remove', NULL),
    ))
    inspect_arguments(Solver.solve_final_state, solve_final_state_args)

    solve_for_diff_args = odict((
        ('self', NULL),
        ('deps_modifier', NULL),
        ('prune', NULL),
        ('ignore_pinned', NULL),
        ('force_remove', NULL),
        ('force_reinstall', False),
    ))
    inspect_arguments(Solver.solve_for_diff, solve_for_diff_args)

    solve_for_transaction_args = odict((
        ('self', NULL),
        ('deps_modifier', NULL),
        ('prune', NULL),
        ('ignore_pinned', NULL),
        ('force_remove', NULL),
        ('force_reinstall', False),
    ))
    inspect_arguments(Solver.solve_for_transaction, solve_for_transaction_args)
