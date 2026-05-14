"""Common collection classes."""

from __future__ import annotations

from functools import reduce
from collections.abc import Callable, Iterable, Mapping, Reversible, Set
from typing import Any, TypeVar, overload

from frozendict import frozendict

from ..deprecations import deprecated
from ..common.compat import isiterable


_T = TypeVar("_T")
_U = TypeVar("_U")
_V = TypeVar("_V")


# http://stackoverflow.com/a/14620633/2127762
class AttrDict(dict):
    """Sub-classes dict, and further allows attribute-like access to dictionary items.

    Examples:
        >>> d = AttrDict({'a': 1})
        >>> d.a, d['a'], d.get('a')
        (1, 1, 1)
        >>> d.b = 2
        >>> d.b, d['b']
        (2, 2)
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.__dict__ = self


@overload
def first(
    seq: Iterable[_T],
    key: Callable[[_T], Any] = bool,
    default: _U | Callable[[], _U] | None = None,
    apply: Callable[[_T], _T] = lambda x: x,
) -> _T | _U | None: ...


@overload
def first(
    seq: Iterable[_T],
    key: Callable[[_T], Any],
    default: _U | Callable[[], _U] | None,
    apply: Callable[[_T], _V],
) -> _V | _U | None: ...


def first(
    seq: Iterable[_T],
    key: Callable[[_T], Any] = bool,
    default: _U | Callable[[], _U] | None = None,
    apply: Callable[[_T], Any] = lambda x: x,
) -> Any:
    """Give the first value that satisfies the key test.

    Args:
        seq (iterable):
        key (callable): test for each element of iterable
        default: returned when all elements fail test
        apply (callable): applied to element before return, but not to default value

    Returns: first element in seq that passes key, mutated with optional apply

    Examples:
        >>> first([0, False, None, [], (), 42])
        42
        >>> first([0, False, None, [], ()]) is None
        True
        >>> first([0, False, None, [], ()], default='ohai')
        'ohai'
        >>> import re
        >>> m = first(re.match(regex, 'abc') for regex in ['b.*', 'a(.*)'])
        >>> m.group(1)
        'bc'

        The optional `key` argument specifies a one-argument predicate function
        like that used for `filter()`.  The `key` argument, if supplied, must be
        in keyword form.  For example:
        >>> first([1, 1, 3, 4, 5], key=lambda x: x % 2 == 0)
        4

    """
    return next(
        (apply(x) for x in seq if key(x)), default() if callable(default) else default
    )


@overload
def last(
    seq: Reversible[_T],
    key: Callable[[_T], Any] = bool,
    default: _U | None = None,
    apply: Callable[[_T], _T] = lambda x: x,
) -> _T | _U | None: ...


@overload
def last(
    seq: Reversible[_T],
    key: Callable[[_T], Any],
    default: _U | None,
    apply: Callable[[_T], _V],
) -> _V | _U | None: ...


def last(
    seq: Reversible[_T],
    key: Callable[[_T], Any] = bool,
    default: _U | None = None,
    apply: Callable[[_T], Any] = lambda x: x,
) -> Any:
    """Give the last value that satisfies the key test.

    Args:
        seq: Reversible collection to inspect.
        key: Test applied to each element.
        default: Returned when all elements fail the test.
        apply: Applied to the matched element before return.

    Returns:
        The last matching element after applying ``apply``, or ``default``.
    """
    return next((apply(x) for x in reversed(seq) if key(x)), default)
