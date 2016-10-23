# -*- coding: utf-8 -*-
from __future__ import print_function, division, absolute_import
from logging import getLogger
from textwrap import dedent

log = getLogger(__name__)


def dals(string):
    """dedent and left-strip"""
    return dedent(string).lstrip()


def find_or_none(key, search_maps, _map_index=0):
    """Return the value of the first key found in the list of search_maps,
    otherwise return None.

    Examples:
        >>> from .collection import AttrDict
        >>> d1 = AttrDict({'a': 1, 'b': 2, 'c': 3, 'e': None})
        >>> d2 = AttrDict({'b': 5, 'e': 6, 'f': 7})
        >>> find_or_none('c', (d1, d2))
        3
        >>> find_or_none('f', (d1, d2))
        7
        >>> find_or_none('b', (d1, d2))
        2
        >>> print(find_or_none('g', (d1, d2)))
        None
        >>> find_or_none('e', (d1, d2))
        6

    """
    try:
        attr = getattr(search_maps[_map_index], key)
        return attr if attr is not None else find_or_none(key, search_maps[1:])
    except AttributeError:
        # not found in first map object, so go to next
        return find_or_none(key, search_maps, _map_index+1)
    except IndexError:
        # ran out of map objects to search
        return None
