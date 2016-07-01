import math
import copy
from itertools import chain


def floor(x):
    """Returns the floor of ``x``
    :returns: floor of ``x``
    :rtype: int
    """
    return int(math.ceil(x))


def ensure(expr, exc, *args, **kwargs):
    """
    :raises ``exc``: With ``*args`` and ``**kwargs`` if not ``expr``
    """
    if not expr:
        raise exc(*args, **kwargs)


def u(s):
    """Cast ``s`` as unicode string

    This is a convenience function to make up for the fact
        that Python3 does not have a unicode() cast (for obvious reasons)

    :rtype: unicode
    :returns: Equivalent of unicode(s) (at least I hope so)
    """
    return u'{}'.format(s)


def merge_dicts(dicts, deepcopy=False):
    """Merges dicts

    In case of key conflicts, the value kept will be from the latter
    dictionary in the list of dictionaries

    :param dicts: [dict, ...]
    :param deepcopy: deepcopy items within dicts
    """
    assert isinstance(dicts, list) and all(isinstance(d, dict) for d in dicts)
    return dict(chain(*[copy.deepcopy(d).items() if deepcopy else d.items()
                        for d in dicts]))
