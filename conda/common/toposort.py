# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Topological sorting implementation."""

from __future__ import annotations

from functools import reduce as _reduce
from logging import getLogger
from typing import TYPE_CHECKING, Hashable, TypeVar

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator, Mapping

log = getLogger(__name__)

T = TypeVar("T", bound=Hashable)


def _toposort(data: dict[T, set[T]]) -> Iterator[T]:
<<<<<<< HEAD
    """Dependencies are expressed as a dictionary whose keys are items
    and whose values are a set of dependent items. Output is a list of
    sets in topological order. The first set consists of items with no
    dependences, each subsequent set consists of items that depend upon
    items in the preceding sets.
=======
    """Yields items in topological order.

    Dependencies are expressed as a dictionary whose keys are items
    and whose values are a set of dependent items.
>>>>>>> 854a08509 (Fix pre-commit: move annotation-only imports to TYPE_CHECKING block)
    """
    # Special case empty input.
    if len(data) == 0:
        return

    # Ignore self dependencies.
    for k, v in data.items():
        v.discard(k)
    # Find all items that don't depend on anything.
    extra_items_in_deps = _reduce(set.union, data.values()) - set(data.keys())
    # Add empty dependences where needed.
    data.update({item: set() for item in extra_items_in_deps})
    while True:
<<<<<<< HEAD
=======
        # sorted() gives deterministic output; assumes keys are orderable (strings in practice)
>>>>>>> 854a08509 (Fix pre-commit: move annotation-only imports to TYPE_CHECKING block)
        ordered = sorted({item for item, dep in data.items() if len(dep) == 0})  # type: ignore[type-var]
        if not ordered:
            break

        for item in ordered:
            yield item
            data.pop(item, None)

        for dep in sorted(data.values()):
            dep -= set(ordered)

    if len(data) != 0:
        from ..exceptions import CondaValueError

        msg = "Cyclic dependencies exist among these items: {}"
        raise CondaValueError(msg.format(" -> ".join(repr(x) for x in data.keys())))


def pop_key(data: dict[T, set[T]]) -> T:
    """
    Pop an item from the graph that has the fewest dependencies in the case of a tie
    The winners will be sorted alphabetically
    """
    items = sorted(data.items(), key=lambda item: (len(item[1]), item[0]))
    key = items[0][0]

    data.pop(key)

    for dep in data.values():
        dep.discard(key)

    return key


def _safe_toposort(data: dict[T, set[T]]) -> Iterator[T]:
<<<<<<< HEAD
    """Dependencies are expressed as a dictionary whose keys are items
    and whose values are a set of dependent items. Output is a list of
    sets in topological order. The first set consists of items with no
    dependencies, each subsequent set consists of items that depend upon
    items in the preceding sets.
=======
    """Yields items in topological order.

    Dependencies are expressed as a dictionary whose keys are items
    and whose values are a set of dependent items.
>>>>>>> 854a08509 (Fix pre-commit: move annotation-only imports to TYPE_CHECKING block)
    """
    # Special case empty input.
    if len(data) == 0:
        return

    t = _toposort(data)

    while True:
        try:
            value = next(t)
            yield value
        except ValueError as err:
            log.debug(err.args[0])

            if not data:
                return  # pragma: no cover

            yield pop_key(data)

            t = _toposort(data)

            continue
        except StopIteration:
            return


def toposort(data: Mapping[T, Iterable[T]], safe: bool = True) -> list[T]:
    """Return a topologically sorted list of items from a dependency graph.

    Dependencies are expressed as a mapping whose keys are items and
    whose values are an iterable of dependent items.
    """
    graph: dict[T, set[T]] = {k: set(v) for k, v in data.items()}

<<<<<<< HEAD
=======
    # This special case assumes string keys; the type: ignore below is intentional.
>>>>>>> 854a08509 (Fix pre-commit: move annotation-only imports to TYPE_CHECKING block)
    if "python" in graph:
        # Special case: Remove circular dependency between python and pip,
        # to ensure python is always installed before anything that needs it.
        # For more details:
        # - https://github.com/conda/conda/issues/1152
        # - https://github.com/conda/conda/pull/1154
        # - https://github.com/conda/conda-build/issues/401
        # - https://github.com/conda/conda/pull/1614
        graph["python"].discard("pip")  # type: ignore[index]

    if safe:
        return list(_safe_toposort(graph))
    else:
        return list(_toposort(graph))
