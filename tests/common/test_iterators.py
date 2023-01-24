# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from itertools import chain

from conda.core.link import PrefixActionGroup


def test_interleave():
    try:
        from tlz.itertoolz import interleave
    except ImportError:
        from conda._vendor.toolz.itertoolz import interleave

    prefix_action_groups = {
        "remove_menu_action_groups": PrefixActionGroup([1, 2], [], [], [], [], [], [], [], []),
        "unlink_action_groups": PrefixActionGroup([], [3, 4], [], [], [], [], [], [], []),
        "unregister_action_groups": PrefixActionGroup([], [], [5, 6], [], [], [], [], [], []),
        "link_action_groups": PrefixActionGroup([], [], [], [7, 8], [], [], [], [], []),
        "register_action_groups": PrefixActionGroup([], [], [], [], [9, 10], [], [], [], []),
        "compile_action_groups": PrefixActionGroup([], [], [], [], [], [11, 12], [], [], []),
        "make_menu_action_groups": PrefixActionGroup([], [], [], [], [], [], [13, 14], [], []),
        "entry_point_action_groups": PrefixActionGroup([], [], [], [], [], [], [], [15, 16], []),
        "prefix_record_groups": PrefixActionGroup([], [], [], [], [], [], [], [], [17, 18]),
        "all": PrefixActionGroup(["a"], ["b"], ["c"], ["d"], ["e"], ["f"], ["g"], ["h"], ["i"]),
    }

    # old style
    old_tuple = tuple(chain.from_iterable(interleave(prefix_action_groups.values())))

    # new style
    new_tuple = tuple(chain(*chain(*zip(*prefix_action_groups.values()))))

    assert old_tuple == new_tuple
