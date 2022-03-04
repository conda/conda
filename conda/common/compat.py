# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
# Try to keep compat small because it's imported by everything
# What is compat, and what isn't?
# If a piece of code is "general" and used in multiple modules, it goes here.
# If it's only used in one module, keep it in that module, preferably near the top.
# This module should contain ONLY stdlib imports.
from __future__ import absolute_import, division, print_function, unicode_literals

from itertools import chain
from operator import methodcaller
import sys
from tempfile import mkdtemp
import warnings as _warnings

on_win = bool(sys.platform == "win32")
on_mac = bool(sys.platform == "darwin")
on_linux = bool(sys.platform == "linux")

PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3
FILESYSTEM_ENCODING = sys.getfilesystemencoding()

# Control some tweakables that will be removed finally.
ENCODE_ENVIRONMENT=True
ENCODE_ARGS=False

# Want bytes encoded as utf-8 for both names and values.
def encode_for_env_var(value):
    if isinstance(value, str):
        return value
    if sys.version_info[0] == 2:
        _unicode = unicode
    else:
        _unicode = str
    if isinstance(value, (str, _unicode)):
        try:
            return bytes(value, encoding='utf-8')
        except:
            return value.encode('utf-8')
    return str(value)


def encode_environment(env):
    if ENCODE_ENVIRONMENT:
        env = {encode_for_env_var(k): encode_for_env_var(v) for k, v in iteritems(env)}
    return env


def encode_arguments(arguments):
    if ENCODE_ARGS:
        arguments = {encode_for_env_var(arg) for arg in arguments}
    return arguments


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
    from collections.abc import Mapping, Sequence
    from io import StringIO
    from itertools import zip_longest
    if sys.version_info[1] >= 5:
        from os import scandir
        from json import JSONDecodeError
        JSONDecodeError = JSONDecodeError
    else:
        from scandir import scandir
        JSONDecodeError = ValueError
elif PY2:  # pragma: py3 no cover
    from collections import Mapping, Sequence
    # We cannot use cStringIO if we ever hope to print Unicode.
    # https://docs.python.org/2.7/library/stringio.html
    # Unlike the memory files implemented by the StringIO module, those provided
    # by this module are not able to accept Unicode strings that cannot be encoded
    # as plain ASCII strings.
    # print(io.StringIO(u'fooáßñ固').read())
    # fooáßñ固
    # vs:
    # print(cStringIO.StringIO(u'fooáßñ固').read())
    # Traceback (most recent call last):
    #   File "<stdin>", line 1, in <module>
    # UnicodeEncodeError: 'ascii' codec can't encode characters in position 3-6: ordinal not in range(128)
    from io import StringIO
    from scandir import scandir
    from itertools import izip as zip, izip_longest as zip_longest
    JSONDecodeError = ValueError

Mapping = Mapping
Sequence = Sequence
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

    from collections.abc import Iterable
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

from collections import OrderedDict as odict  # NOQA
odict = odict

from io import open as io_open  # NOQA


def open(file, mode='r', buffering=-1, encoding=None, errors=None, newline=None, closefd=True):
    if 'b' in mode:
        return io_open(file, str(mode), buffering=buffering,
                       errors=errors, newline=newline, closefd=closefd)
    else:
        return io_open(file, str(mode), buffering=buffering,
                       encoding=encoding or 'utf-8', errors=errors, newline=newline,
                       closefd=closefd)


def six_with_metaclass(meta, *bases):
    """Create a base class with a metaclass."""
    # This requires a bit of explanation: the basic idea is to make a dummy
    # metaclass for one level of class instantiation that replaces itself with
    # the actual metaclass.
    class metaclass(type):

        def __new__(cls, name, this_bases, d):
            return meta(name, bases, d)

        @classmethod
        def __prepare__(cls, name, this_bases):
            return meta.__prepare__(name, bases)
    return type.__new__(metaclass, str('temporary_class'), (), {})


NoneType = type(None)
primitive_types = tuple(chain(string_types, integer_types, (float, complex, bool, NoneType)))


def _init_stream_encoding(stream):
    # PY2 compat: Initialize encoding for an IO stream.
    # Python 2 sets the encoding of stdout/stderr to None if not run in a
    # terminal context and thus falls back to ASCII.
    if not PY2 or not isinstance(stream, file) or stream.encoding:
        return stream
    from codecs import getwriter
    from locale import getpreferredencoding
    # No no no.
    encoding = getpreferredencoding()
    # encoding = 'UTF-8'
    try:
        writer_class = getwriter(encoding)
    except LookupError:
        writer_class = getwriter("UTF-8")
    return writer_class(stream)


def init_std_stream_encoding():
    sys.stdout = _init_stream_encoding(sys.stdout)
    sys.stderr = _init_stream_encoding(sys.stderr)


def ensure_binary(value):
    try:
        return value.encode('utf-8')
    except AttributeError:  # pragma: no cover
        # AttributeError: '<>' object has no attribute 'encode'
        # In this case assume already binary type and do nothing
        return value


def ensure_text_type(value):
    try:
        return value.decode('utf-8')
    except AttributeError:  # pragma: no cover
        # AttributeError: '<>' object has no attribute 'decode'
        # In this case assume already text_type and do nothing
        return value
    except UnicodeDecodeError:  # pragma: no cover
        try:
            from chardet import detect
        except ImportError:
            try:
                from requests.packages.chardet import detect
            except ImportError:  # pragma: no cover
                from pip._vendor.requests.packages.chardet import detect
        encoding = detect(value).get('encoding') or 'utf-8'
        return value.decode(encoding, errors='replace')
    except UnicodeEncodeError:  # pragma: no cover
        # it's already text_type, so ignore?
        # not sure, surfaced with tests/models/test_match_spec.py test_tarball_match_specs
        # using py27
        return value


def ensure_unicode(value):
    try:
        return value.decode('unicode_escape')
    except AttributeError:  # pragma: no cover
        # AttributeError: '<>' object has no attribute 'decode'
        # In this case assume already unicode and do nothing
        return value


def ensure_fs_path_encoding(value):
    try:
        return value.encode(FILESYSTEM_ENCODING)
    except AttributeError:
        return value
    except UnicodeEncodeError:
        return value


def ensure_utf8_encoding(value):
    try:
        return value.encode('utf-8')
    except AttributeError:
        return value
    except UnicodeEncodeError:
        return value
