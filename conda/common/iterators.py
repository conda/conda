# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Replacements for parts of the toolz library."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..deprecations import deprecated

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable
    from typing import Any, TypeVar

    T = TypeVar("T")
    K = TypeVar("K")


@deprecated.argument(
    "26.9",
    "27.3",
    "sequence",
    rename="iterable",
    addendum="Use `collections.defaultdict` instead.",
)
def groupby_to_dict(
    keyfunc: Callable[[T], K], iterable: Iterable[T]
) -> dict[K, list[T]]:
    """A `toolz`-style groupby implementation.

    Returns a dictionary of { key: [group] } instead of iterators.
    """
    from collections import defaultdict
    from itertools import groupby

    result: dict[K, list[T]] = defaultdict(list)
    for key, group in groupby(iterable, keyfunc):
        result[key].extend(group)
    return dict(result)


def unique(iterable: Iterable[T]) -> Iterable[T]:
    """A `toolz` inspired `unique` implementation.

    Returns a generator of unique elements in the sequence
    """
    seen: set[Any] = set()
    yield from (
        # seen.add always returns None so we will always return element
        seen.add(element) or element
        for element in iterable
        # only pass along novel elements
        if element not in seen
    )
