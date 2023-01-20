# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import warnings


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
