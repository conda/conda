# -*- coding: utf-8 -*-
# Try to keep compat small because it's imported by everything
# What is compat, and what isn't?
# If a piece of code is "general" and used in multiple modules, it goes here.
# If it's only used in one module, keep it in that module, preferably near the top.
from __future__ import absolute_import, division, print_function, unicode_literals

from itertools import chain
from operator import methodcaller
import sys

on_win = bool(sys.platform == "win32")

PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3


# #############################
# equivalent commands
# #############################

if PY3:  # pragma: py2 no cover
    string_types = str,
    integer_types = int,
    class_types = type,
    text_type = str
    binary_type = bytes
    input = input
    range = range

elif PY2:  # pragma: py3 no cover
    from types import ClassType
    string_types = basestring,
    integer_types = (int, long)
    class_types = (type, ClassType)
    text_type = unicode
    binary_type = str
    input = raw_input
    range = xrange


# #############################
# equivalent imports
# #############################

if PY3:  # pragma: py2 no cover
    from io import StringIO
    from itertools import zip_longest
elif PY2:  # pragma: py3 no cover
    from cStringIO import StringIO
    from itertools import izip as zip, izip_longest as zip_longest

StringIO = StringIO
zip = zip
zip_longest = zip_longest


# #############################
# equivalent functions
# #############################

if PY3:  # pragma: py2 no cover
    def iterkeys(d, **kw):
        return iter(d.keys(**kw))

    def itervalues(d, **kw):
        return iter(d.values(**kw))

    def iteritems(d, **kw):
        return iter(d.items(**kw))

    viewkeys = methodcaller("keys")
    viewvalues = methodcaller("values")
    viewitems = methodcaller("items")

    from collections import Iterable
    def isiterable(obj):
        return not isinstance(obj, string_types) and isinstance(obj, Iterable)

elif PY2:  # pragma: py3 no cover
    def iterkeys(d, **kw):
        return d.iterkeys(**kw)

    def itervalues(d, **kw):
        return d.itervalues(**kw)

    def iteritems(d, **kw):
        return d.iteritems(**kw)

    viewkeys = methodcaller("viewkeys")
    viewvalues = methodcaller("viewvalues")
    viewitems = methodcaller("viewitems")

    def isiterable(obj):
        return (hasattr(obj, '__iter__')
                and not isinstance(obj, string_types)
                and type(obj) is not type)


# #############################
# other
# #############################

def with_metaclass(Type, skip_attrs=set(('__dict__', '__weakref__'))):
    """Class decorator to set metaclass.

    Works with both Python 2 and Python 3 and it does not add
    an extra class in the lookup order like ``six.with_metaclass`` does
    (that is -- it copies the original class instead of using inheritance).

    """

    def _clone_with_metaclass(Class):
        attrs = dict((key, value) for key, value in iteritems(vars(Class))
                     if key not in skip_attrs)
        return Type(Class.__name__, Class.__bases__, attrs)

    return _clone_with_metaclass


from collections import OrderedDict as odict
odict = odict

NoneType = type(None)
primitive_types = tuple(chain(string_types, integer_types, (float, complex, bool, NoneType)))


def ensure_binary(value):
    try:
        return value.encode('utf-8')
    except AttributeError:
        # AttributeError: '<>' object has no attribute 'encode'
        # In this case assume already binary type and do nothing
        return value


def ensure_text_type(value):
    try:
        return value.decode('utf-8')
    except AttributeError:
        # AttributeError: '<>' object has no attribute 'decode'
        # In this case assume already text_type and do nothing
        return value
    except UnicodeDecodeError:
        from requests.packages.chardet import detect
        encoding = detect(value).get('encoding') or 'utf-8'
        return value.decode(encoding)


def ensure_unicode(value):
    try:
        return value.decode('unicode_escape')
    except AttributeError:
        # AttributeError: '<>' object has no attribute 'decode'
        # In this case assume already unicode and do nothing
        return value
