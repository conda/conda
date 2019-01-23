# -*- coding: utf-8 -*-
"""Common collection classes."""
from __future__ import print_function, division, absolute_import
from functools import reduce
try:
    from collections.abc import Mapping, Set
except ImportError:
    from collections import Mapping, Set

from .compat import isiterable, iteritems, odict, text_type


def make_immutable(value):
    # this function is recursive, and if nested data structures fold back on themselves,
    #   there will likely be recursion errors
    if isinstance(value, Mapping):
        if isinstance(value, frozendict):
            return value
        return frozendict((k, make_immutable(v)) for k, v in iteritems(value))
    elif isinstance(value, Set):
        if isinstance(value, frozenset):
            return value
        return frozenset(make_immutable(v) for v in value)
    elif isiterable(value):
        if isinstance(value, tuple):
            return value
        return tuple(make_immutable(v) for v in value)
    else:
        return value


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
    def __init__(self, *args, **kwargs):
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self


class frozendict(odict):

    def __key(self):
        return tuple((k, self[k]) for k in sorted(self))

    def __hash__(self):
        return hash(self.__key())

    def __eq__(self, other):
        try:
            return self.__key() == other.__key()
        except AttributeError:
            if isinstance(other, Mapping):
                return self.__key() == frozendict(other).__key()
            return False


def first(seq, key=lambda x: bool(x), default=None, apply=lambda x: x):
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
    return next((apply(x) for x in seq if key(x)), default() if callable(default) else default)


def firstitem(map, key=lambda k, v: bool(k), default=None, apply=lambda k, v: (k, v)):
    return next((apply(k, v) for k, v in map if key(k, v)), default)


def last(seq, key=lambda x: bool(x), default=None, apply=lambda x: x):
    return next((apply(x) for x in reversed(seq) if key(x)), default)


def call_each(seq):
    """Calls each element of sequence to invoke the side effect.

    Args:
        seq:

    Returns: None

    """
    try:
        reduce(lambda _, y: y(), seq)
    except TypeError as e:
        if text_type(e) != "reduce() of empty sequence with no initial value":
            raise
