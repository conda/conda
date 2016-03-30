"""
For compatibility between Python versions.
Taken mostly from six.py by Benjamin Peterson.
"""

import sys
import types
import os

# True if we are running on Python 3.
PY3 = sys.version_info[0] == 3

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
    import urllib.parse as urlparse
    from urllib.parse import quote as urllib_quote
    from itertools import zip_longest
    from math import log2, ceil
    from shlex import quote
    from tempfile import TemporaryDirectory
    range = range
    zip = zip
else:
    import ConfigParser as configparser
    from cStringIO import StringIO
    import urlparse
    from urllib import quote as urllib_quote
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
    def log2(x):
        return log(x, 2)
    def ceil(x):
        from math import ceil
        return int(ceil(x))
    from pipes import quote

    # Modified from http://hg.python.org/cpython/file/3.3/Lib/tempfile.py. Don't
    # use the 3.4 one. It uses the new weakref.finalize feature.
    import shutil as _shutil
    import warnings as _warnings
    import os as _os
    from tempfile import mkdtemp
    range = xrange
    from itertools import izip as zip

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
            if self.name and not self._closed:
                try:
                    _shutil.rmtree(self.name)
                except (TypeError, AttributeError) as ex:
                    if "None" not in '%s' % (ex,):
                        raise
                    self._rmtree(self.name)
                self._closed = True
                if _warn and _warnings.warn:
                    _warnings.warn("Implicitly cleaning up {!r}".format(self),
                                   ResourceWarning)

        def __exit__(self, exc, value, tb):
            self.cleanup()

        def __del__(self):
            # Issue a ResourceWarning if implicit cleanup needed
            self.cleanup(_warn=True)

        def _rmtree(self, path, _OSError=OSError, _sep=_os.path.sep,
                    _listdir=_os.listdir, _remove=_os.remove, _rmdir=_os.rmdir):
            # Essentially a stripped down version of shutil.rmtree.  We can't
            # use globals because they may be None'ed out at shutdown.
            if not isinstance(path, str):
                _sep = _sep.encode()
            try:
                for name in _listdir(path):
                    fullname = path + _sep + name
                    try:
                        _remove(fullname)
                    except _OSError:
                        self._rmtree(fullname)
                _rmdir(path)
            except _OSError:
                pass

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

def get_http_value(u, key):
    if PY3:
        return u.headers.get(key)
    else:
        return u.info().getheader(key)

def with_metaclass(meta, *bases):
    """
    Create a base class with a metaclass.

    For example, if you have the metaclass

    >>> class Meta(type):
    ...     pass

    Use this as the metaclass by doing

    >>> from sympy.core.compatibility import with_metaclass
    >>> class MyClass(with_metaclass(Meta, object)):
    ...     pass

    This is equivalent to the Python 2::

        class MyClass(object):
            __metaclass__ = Meta

    or Python 3::

        class MyClass(object, metaclass=Meta):
            pass

    That is, the first argument is the metaclass, and the remaining arguments
    are the base classes. Note that if the base class is just ``object``, you
    may omit it.

    >>> MyClass.__mro__
    (<class 'MyClass'>, <... 'object'>)
    >>> type(MyClass)
    <class 'Meta'>

    """
    class metaclass(meta):
        __call__ = type.__call__
        __init__ = type.__init__
        def __new__(cls, name, this_bases, d):
            if this_bases is None:
                return type.__new__(cls, name, (), d)
            return meta(name, bases, d)
    return metaclass("NewBase", None, {})
