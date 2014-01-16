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
        except (TypeError, NotImplementedError):
            # On systems that don't allow permissions on symbolic links, skip
            # links entirely.
            if not os.path.islink(path):
                os.chmod(path, mode)
    import configparser
    from io import StringIO
    import urllib.parse as urlparse

else:
    import ConfigParser as configparser
    from cStringIO import StringIO
    import urlparse
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
