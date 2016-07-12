"""This module provides useful math functions on top of Python's
built-in :mod:`math` module.
"""
from math import ceil as _ceil, floor as _floor
import bisect


def ceil(x, options=None):
    """Return the ceiling of *x*. If *options* is set, return the smallest
    integer or float from *options* that is greater than or equal to
    *x*.

    Args:
        x (int or float): Number to be tested.
        options (iterable): Optional iterable of arbitrary numbers
          (ints or floats).

    >>> VALID_CABLE_CSA = [1.5, 2.5, 4, 6, 10, 25, 35, 50]
    >>> ceil(3.5, options=VALID_CABLE_CSA)
    4
    >>> ceil(4, options=VALID_CABLE_CSA)
    4
    """
    if options is None:
        return _ceil(x)
    options = sorted(options)
    i = bisect.bisect_left(options, x)
    if i == len(options):
        raise ValueError("no ceil options greater than or equal to: %r" % x)
    return options[i]


def floor(x, options=None):
    """Return the floor of *x*. If *options* is set, return the largest
    integer or float from *options* that is less than or equal to
    *x*.

    Args:
        x (int or float): Number to be tested.
        options (iterable): Optional iterable of arbitrary numbers
          (ints or floats).

    >>> VALID_CABLE_CSA = [1.5, 2.5, 4, 6, 10, 25, 35, 50]
    >>> floor(3.5, options=VALID_CABLE_CSA)
    2.5
    >>> floor(2.5, options=VALID_CABLE_CSA)
    2.5

    """
    if options is None:
        return _floor(x)
    options = sorted(options)

    i = bisect.bisect_right(options, x)
    if not i:
        raise ValueError("no floor options less than or equal to: %r" % x)
    return options[i - 1]
