# This module is only being maintained for conda-build compatibility
from __future__ import absolute_import, division, print_function, unicode_literals
import warnings as _warnings
from tempfile import mkdtemp


# shim for conda-build
from .common.compat import *
PY3 = PY3


if PY3:
    import configparser
else:
    import ConfigParser as configparser
configparser = configparser


from .gateways.disk.link import lchmod  # NOQA
lchmod = lchmod


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
        from .gateways.disk.delete import rm_rf as _rm_rf
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
