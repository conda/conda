# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

"""
Replacements for parts of the toolz library.
"""

import itertools
import collections
from collections.abc import Iterable
from typing import TypeVar, Any


def groupby_to_dict(keyfunc, sequence):
    """
    toolz-style groupby, returns a dictionary of { key: [group] } instead of
    iterators.
    """
    result = collections.defaultdict(list)
    for key, group in itertools.groupby(sequence, keyfunc):
        result[key].extend(group)
    return dict(result)


T = TypeVar("T")


def next_instance(objects: Iterable[Any], object_type: type[T]) -> T | None:
    """
    Iterates over ``objects`` and picks the first ``object_type`` encountered.
    Returns ``None`` if no instances have been found.

    Examples:
        >>> next_instance([1, 2, 3, "4"], str)
        '4'
        >>> next_instance([1, 2, 3], str)
        None
        >>> next_instance(range(10), str)  # Test using generator expression
        None
        >>> next_instance(('1', 2, {3}, {'4': 'four'}), dict)
        {'4': 'four'}
    """
    return next((obj for obj in objects if isinstance(obj, object_type)), None)
