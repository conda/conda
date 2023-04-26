# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import warnings
from itertools import chain

from conda.core.link import PrefixActionGroup


def test_unpacking_for_merge():
    warnings.warn(
        "`toolz` is pending deprecation and will be removed in a future release.",
        PendingDeprecationWarning,
    )

    try:
        from tlz.dicttoolz import merge
    except ImportError:
        from conda._vendor.toolz.dicttoolz import merge

    # data
    first_mapping = {"a": "a", "b": "b", "c": "c"}
    second_mapping = {"d": "d", "e": "e"}
    third_mapping = {"a": 1, "e": 2}

    # old style
    old_merge = merge((first_mapping, second_mapping, third_mapping))

    # new style
    new_merge = {**first_mapping, **second_mapping, **third_mapping}

    assert old_merge == new_merge


def test_unpacking_for_merge_with():
    warnings.warn(
        "`toolz` is pending deprecation and will be removed in a future release.",
        PendingDeprecationWarning,
    )

    try:
        from tlz.dicttoolz import merge_with
    except ImportError:
        from conda._vendor.toolz.dicttoolz import merge_with

    # data
    mappings = [
        {"a": 1, "b": 2, "c": 3},
        {"d": 4, "e": 5},
        {"a": 6, "e": 7},
    ]

    # old style
    old_merge = merge_with(sum, mappings)

    # new style
    grouped_map = {}
    for mapping in mappings:
        for key, value in mapping.items():
            grouped_map.setdefault(key, []).append(value)
    new_merge = {key: sum(values) for key, values in grouped_map.items()}

    assert old_merge == new_merge


def test_interleave():
    try:
        from tlz.itertoolz import interleave
    except ImportError:
        from conda._vendor.toolz.itertoolz import interleave

    prefix_action_groups = {
        "remove_menu_action_groups": PrefixActionGroup(
            [1, 2], [], [], [], [], [], [], [], []
        ),
        "unlink_action_groups": PrefixActionGroup(
            [], [3, 4], [], [], [], [], [], [], []
        ),
        "unregister_action_groups": PrefixActionGroup(
            [], [], [5, 6], [], [], [], [], [], []
        ),
        "link_action_groups": PrefixActionGroup([], [], [], [7, 8], [], [], [], [], []),
        "register_action_groups": PrefixActionGroup(
            [], [], [], [], [9, 10], [], [], [], []
        ),
        "compile_action_groups": PrefixActionGroup(
            [], [], [], [], [], [11, 12], [], [], []
        ),
        "make_menu_action_groups": PrefixActionGroup(
            [], [], [], [], [], [], [13, 14], [], []
        ),
        "entry_point_action_groups": PrefixActionGroup(
            [], [], [], [], [], [], [], [15, 16], []
        ),
        "prefix_record_groups": PrefixActionGroup(
            [], [], [], [], [], [], [], [], [17, 18]
        ),
        "all": PrefixActionGroup(
            ["a"], ["b"], ["c"], ["d"], ["e"], ["f"], ["g"], ["h"], ["i"]
        ),
    }

    # old style
    old_tuple = tuple(chain.from_iterable(interleave(prefix_action_groups.values())))

    # new style
    new_tuple = tuple(chain(*chain(*zip(*prefix_action_groups.values()))))

    assert old_tuple == new_tuple
