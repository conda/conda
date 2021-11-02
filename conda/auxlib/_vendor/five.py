# -*- coding: utf-8 -*-
"""
    amqp.five
    ~~~~~~~~~~~

    Compatibility implementations of features
    only available in newer Python versions.


"""
from __future__ import absolute_import

import io
import sys

try:
    from collections import Counter
except ImportError:  # pragma: no cover
    from collections import defaultdict

    def Counter():  # noqa
        return defaultdict(int)

try:
    buffer_t = buffer
except NameError:  # pragma: no cover
    # Py3 does not have buffer, only use this for isa checks.

    class buffer_t(object):  # noqa
        pass

bytes_t = bytes

__all__ = ['Counter', 'reload', 'UserList', 'UserDict',
           'Queue', 'Empty', 'Full', 'LifoQueue', 'builtins',
           'zip_longest', 'map', 'zip', 'string', 'string_t', 'bytes_t',
           'long_t', 'text_t', 'int_types', 'module_name_t',
           'range', 'items', 'keys', 'values', 'nextfun', 'reraise',
           'WhateverIO', 'with_metaclass', 'open_fqdn', 'StringIO',
           'THREAD_TIMEOUT_MAX', 'format_d', 'monotonic', 'buffer_t']


#  ############# py3k ########################################################
PY3 = sys.version_info[0] == 3

try:
    reload = reload                         # noqa
except NameError:                           # pragma: no cover
    from imp import reload                  # noqa

try:
    from collections import UserList        # noqa
except ImportError:                         # pragma: no cover
    from UserList import UserList           # noqa

try:
    from collections import UserDict        # noqa
except ImportError:                         # pragma: no cover
    from UserDict import UserDict           # noqa

#  ############# time.monotonic #############################################

if sys.version_info < (3, 3):

    import platform
    SYSTEM = platform.system()

    try:
        import ctypes
    except ImportError:  # pragma: no cover
        ctypes = None  # noqa

    if SYSTEM == 'Darwin' and ctypes is not None:
        from ctypes.util import find_library
        libSystem = ctypes.CDLL(find_library('libSystem.dylib'))
        CoreServices = ctypes.CDLL(find_library('CoreServices'),
                                   use_errno=True)
        mach_absolute_time = libSystem.mach_absolute_time
        mach_absolute_time.restype = ctypes.c_uint64
        absolute_to_nanoseconds = CoreServices.AbsoluteToNanoseconds
        absolute_to_nanoseconds.restype = ctypes.c_uint64
        absolute_to_nanoseconds.argtypes = [ctypes.c_uint64]

        def _monotonic():
            return absolute_to_nanoseconds(mach_absolute_time()) * 1e-9

    elif SYSTEM == 'Linux' and ctypes is not None:
        # from stackoverflow:
        # questions/1205722/how-do-i-get-monotonic-time-durations-in-python
        import os

        CLOCK_MONOTONIC = 1  # see <linux/time.h>

        class timespec(ctypes.Structure):
            _fields_ = [
                ('tv_sec', ctypes.c_long),
                ('tv_nsec', ctypes.c_long),
            ]

        librt = ctypes.CDLL('librt.so.1', use_errno=True)
        clock_gettime = librt.clock_gettime
        clock_gettime.argtypes = [
            ctypes.c_int, ctypes.POINTER(timespec),
        ]

        def _monotonic():  # noqa
            t = timespec()
            if clock_gettime(CLOCK_MONOTONIC, ctypes.pointer(t)) != 0:
                errno_ = ctypes.get_errno()
                raise OSError(errno_, os.strerror(errno_))
            return t.tv_sec + t.tv_nsec * 1e-9
    else:
        from time import time as _monotonic
try:
    from time import monotonic
except ImportError:
    monotonic = _monotonic  # noqa

# ############# Py3 <-> Py2 #################################################

if PY3:  # pragma: no cover
    import builtins

    from itertools import zip_longest

    map = map
    zip = zip
    string = str
    string_t = str
    long_t = int
    text_t = str
    range = range
    int_types = (int,)
    module_name_t = str

    open_fqdn = 'builtins.open'

    def items(d):
        return d.items()

    def keys(d):
        return d.keys()

    def values(d):
        return d.values()

    def nextfun(it):
        return it.__next__

    exec_ = getattr(builtins, 'exec')

    def reraise(tp, value, tb=None):
        if value.__traceback__ is not tb:
            raise value.with_traceback(tb)
        raise value

else:
    import __builtin__ as builtins  # noqa
    from itertools import (               # noqa
        imap as map,
        izip as zip,
        izip_longest as zip_longest,
    )

    string = unicode                # noqa
    string_t = basestring           # noqa
    text_t = unicode
    long_t = long                   # noqa
    range = xrange
    module_name_t = str
    int_types = (int, long)

    open_fqdn = '__builtin__.open'

    def items(d):                   # noqa
        return d.iteritems()

    def keys(d):                    # noqa
        return d.iterkeys()

    def values(d):                  # noqa
        return d.itervalues()

    def nextfun(it):                # noqa
        return it.next

    def exec_(code, globs=None, locs=None):  # pragma: no cover
        """Execute code in a namespace."""
        if globs is None:
            frame = sys._getframe(1)
            globs = frame.f_globals
            if locs is None:
                locs = frame.f_locals
            del frame
        elif locs is None:
            locs = globs
        exec("""exec code in globs, locs""")

    exec_("""def reraise(tp, value, tb=None): raise tp, value, tb""")


def with_metaclass(Type, skip_attrs=set(('__dict__', '__weakref__'))):
    """Class decorator to set metaclass.

    Works with both Python 2 and Python 3 and it does not add
    an extra class in the lookup order like ``six.with_metaclass`` does
    (that is -- it copies the original class instead of using inheritance).

    """

    def _clone_with_metaclass(Class):
        attrs = dict((key, value) for key, value in items(vars(Class))
                     if key not in skip_attrs)
        return Type(Class.__name__, Class.__bases__, attrs)

    return _clone_with_metaclass

# ############# threading.TIMEOUT_MAX ########################################
try:
    from threading import TIMEOUT_MAX as THREAD_TIMEOUT_MAX
except ImportError:
    THREAD_TIMEOUT_MAX = 1e10  # noqa

# ############# format(int, ',d') ############################################

if sys.version_info >= (2, 7):  # pragma: no cover
    def format_d(i):
        return format(i, ',d')
else:  # pragma: no cover
    def format_d(i):  # noqa
        s = '%d' % i
        groups = []
        while s and s[-1].isdigit():
            groups.append(s[-3:])
            s = s[:-3]
        return s + ','.join(reversed(groups))

StringIO = io.StringIO
_SIO_write = StringIO.write
_SIO_init = StringIO.__init__


class WhateverIO(StringIO):

    def __init__(self, v=None, *a, **kw):
        _SIO_init(self, v.decode() if isinstance(v, bytes) else v, *a, **kw)

    def write(self, data):
        _SIO_write(self, data.decode() if isinstance(data, bytes) else data)