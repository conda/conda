# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function

import collections
from itertools import chain

from ._vendor.five import WhateverIO as StringIO, with_metaclass
from ._vendor.six import (PY2, PY3, integer_types, iteritems, iterkeys, itervalues, string_types,
                          text_type, wraps)
StringIO, with_metaclass = StringIO, with_metaclass
PY2, PY3, integer_types, iteritems, iterkeys, itervalues, string_types = PY2, PY3, integer_types, iteritems, iterkeys, itervalues, string_types  # NOQA
text_type, wraps = text_type, wraps

try:
    from collections import OrderedDict as odict  # NOQA
except ImportError:
    from ordereddict import OrderedDict as odict  # NOQA


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
