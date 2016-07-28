# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function
from itertools import chain
import collections

try:
    from collections import OrderedDict as odict  # NOQA
except ImportError:
    from ordereddict import OrderedDict as odict  # NOQA

from ._vendor.five import with_metaclass, WhateverIO as StringIO  # NOQA
from ._vendor.six import (string_types, text_type, integer_types, iteritems, itervalues,  # NOQA
                          iterkeys, wraps, PY2, PY3)  # NOQA

NoneType = type(None)
primitive_types = tuple(chain(string_types, integer_types, (float, complex, bool, NoneType)))


def isiterable(obj):
    # and not a string
    if PY2:
        return (hasattr(obj, '__iter__')
                and not isinstance(obj, string_types)
                and type(obj) is not type)
    else:
        return not isinstance(obj, string_types) and isinstance(obj, collections.Iterable)
