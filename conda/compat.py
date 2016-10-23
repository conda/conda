"""
For compatibility between Python versions.
Taken mostly from six.py by Benjamin Peterson.
"""
from __future__ import absolute_import, division, print_function, unicode_literals

import sys
import types
import os
import warnings as _warnings
from tempfile import mkdtemp

# True if we are running on Python 3.
PY3 = sys.version_info[0] == 3


class TemporaryDirectory(object):
    """Create and return a temporary directory.  This has the same
    behavior as mkdtemp but can be used as a context manager.  For
    example:

        with TemporaryDirectory() as tmpdir:
            ...

    Upon exiting the context, the directory and everything contained
    in it are removed.
    """

    # Handle mkdtemp raising an exception
    name = None
    _closed = False

    def __init__(self, suffix="", prefix='tmp', dir=None):
        self.name = mkdtemp(suffix, prefix, dir)

    def __repr__(self):
        return "<{} {!r}>".format(self.__class__.__name__, self.name)

    def __enter__(self):
        return self.name

    def cleanup(self, _warn=False, _warnings=_warnings):
        from .common.disk import rm_rf as _rm_rf
        if self.name and not self._closed:
            try:
                _rm_rf(self.name)
            except (TypeError, AttributeError) as ex:
                if "None" not in '%s' % (ex,):
                    raise
                _rm_rf(self.name)
            self._closed = True
            if _warn and _warnings.warn:
                _warnings.warn("Implicitly cleaning up {!r}".format(self),
                                _warnings.ResourceWarning)

    def __exit__(self, exc, value, tb):
        self.cleanup()

    def __del__(self):
        # Issue a ResourceWarning if implicit cleanup needed
        self.cleanup(_warn=True)


if PY3:
    string_types = str,
    integer_types = int,
    class_types = type,
    text_type = str
    binary_type = bytes
    input = input
    def lchmod(path, mode):
        try:
            os.chmod(path, mode, follow_symlinks=False)
        except (TypeError, NotImplementedError, SystemError):
            # On systems that don't allow permissions on symbolic links, skip
            # links entirely.
            if not os.path.islink(path):
                os.chmod(path, mode)
    import configparser
    from io import StringIO
    from itertools import zip_longest
    from shlex import quote
    range = range
    zip = zip

else:
    import ConfigParser as configparser
    from cStringIO import StringIO
    string_types = basestring,
    integer_types = (int, long)
    class_types = (type, types.ClassType)
    text_type = unicode
    binary_type = str
    input = raw_input
    try:
        lchmod = os.lchmod
    except AttributeError:
        def lchmod(path, mode):
            # On systems that don't allow permissions on symbolic links, skip
            # links entirely.
            if not os.path.islink(path):
                os.chmod(path, mode)
    from itertools import izip_longest as zip_longest
    from math import log
    from pipes import quote

    # Modified from http://hg.python.org/cpython/file/3.3/Lib/tempfile.py. Don't
    # use the 3.4 one. It uses the new weakref.finalize feature.
    from tempfile import mkdtemp
    range = xrange
    # used elsewhere - do not remove
    from itertools import izip as zip


if PY3:
    _iterkeys = "keys"
    _itervalues = "values"
    _iteritems = "items"
else:
    _iterkeys = "iterkeys"
    _itervalues = "itervalues"
    _iteritems = "iteritems"


def iterkeys(d):
    """Return an iterator over the keys of a dictionary."""
    return iter(getattr(d, _iterkeys)())

def itervalues(d):
    """Return an iterator over the values of a dictionary."""
    return iter(getattr(d, _itervalues)())

def iteritems(d):
    """Return an iterator over the (key, value) pairs of a dictionary."""
    return iter(getattr(d, _iteritems)())
