# -*- coding: utf-8 -*-
# Try to keep compat small because it's imported by everything
# What is compat, and what isn't?
# If a piece of code is "general" and used in multiple modules, it goes here.
# If it's only used in one module, keep it in that module, preferably near the top.
from __future__ import absolute_import, division, print_function, unicode_literals

from itertools import chain
from operator import methodcaller
from os import chmod, lstat
from os.path import islink
import sys

on_win = bool(sys.platform == "win32")

PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3


# #############################
# equivalent commands
# #############################

if PY3:
    string_types = str,
    integer_types = int,
    class_types = type,
    text_type = str
    binary_type = bytes
    input = input
    range = range

elif PY2:
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

if PY3:
    from io import StringIO
    from itertools import zip_longest
elif PY2:
    from cStringIO import StringIO
    from itertools import izip as zip, izip_longest as zip_longest

StringIO = StringIO
zip = zip
zip_longest = zip_longest


# #############################
# equivalent functions
# #############################

if PY3:
    def iterkeys(d, **kw):
        return iter(d.keys(**kw))

    def itervalues(d, **kw):
        return iter(d.values(**kw))

    def iteritems(d, **kw):
        return iter(d.items(**kw))

    viewkeys = methodcaller("keys")
    viewvalues = methodcaller("values")
    viewitems = methodcaller("items")

    def lchmod(path, mode):
        try:
            chmod(path, mode, follow_symlinks=False)
        except (TypeError, NotImplementedError, SystemError):
            # On systems that don't allow permissions on symbolic links, skip
            # links entirely.
            if not islink(path):
                chmod(path, mode)


    from collections import Iterable
    def isiterable(obj):
        return not isinstance(obj, string_types) and isinstance(obj, Iterable)

elif PY2:
    def iterkeys(d, **kw):
        return d.iterkeys(**kw)

    def itervalues(d, **kw):
        return d.itervalues(**kw)

    def iteritems(d, **kw):
        return d.iteritems(**kw)

    viewkeys = methodcaller("viewkeys")
    viewvalues = methodcaller("viewvalues")
    viewitems = methodcaller("viewitems")

    try:
        from os import lchmod as os_lchmod
        lchmod = os_lchmod
    except ImportError:
        def lchmod(path, mode):
            # On systems that don't allow permissions on symbolic links, skip
            # links entirely.
            if not islink(path):
                chmod(path, mode)

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
    return value.encode('utf-8') if hasattr(value, 'encode') else value


def ensure_text_type(value):
    return value.decode('utf-8') if hasattr(value, 'decode') else value


def ensure_unicode(value):
    return value.decode('unicode_escape') if hasattr(value, 'decode') else value


# TODO: move this somewhere else
# work-around for python bug on Windows prior to python 3.2
# https://bugs.python.org/issue10027
# Adapted from the ntfsutils package, Copyright (c) 2012, the Mozilla Foundation
class CrossPlatformStLink(object):
    _st_nlink = None

    def __call__(self, path):
        return self.st_nlink(path)

    @classmethod
    def st_nlink(cls, path):
        if cls._st_nlink is None:
            cls._initialize()
        return cls._st_nlink(path)

    @classmethod
    def _standard_st_nlink(cls, path):
        return lstat(path).st_nlink

    @classmethod
    def _windows_st_nlink(cls, path):
        st_nlink = cls._standard_st_nlink(path)
        if st_nlink != 0:
            return st_nlink
        else:
            # cannot trust python on Windows when st_nlink == 0
            # get value using windows libraries to be sure of its true value
            # Adapted from the ntfsutils package, Copyright (c) 2012, the Mozilla Foundation
            GENERIC_READ = 0x80000000
            FILE_SHARE_READ = 0x00000001
            OPEN_EXISTING = 3
            hfile = cls.CreateFile(path, GENERIC_READ, FILE_SHARE_READ, None,
                                   OPEN_EXISTING, 0, None)
            if hfile is None:
                from ctypes import WinError
                raise WinError()
            info = cls.BY_HANDLE_FILE_INFORMATION()
            rv = cls.GetFileInformationByHandle(hfile, info)
            cls.CloseHandle(hfile)
            if rv == 0:
                from ctypes import WinError
                raise WinError()
            return info.nNumberOfLinks

    @classmethod
    def _initialize(cls):
        if not on_win:
            cls._st_nlink = cls._standard_st_nlink
        else:
            # http://msdn.microsoft.com/en-us/library/windows/desktop/aa363858
            import ctypes
            from ctypes import POINTER
            from ctypes.wintypes import DWORD, HANDLE, BOOL

            cls.CreateFile = ctypes.windll.kernel32.CreateFileW
            cls.CreateFile.argtypes = [ctypes.c_wchar_p, DWORD, DWORD, ctypes.c_void_p,
                                       DWORD, DWORD, HANDLE]
            cls.CreateFile.restype = HANDLE

            # http://msdn.microsoft.com/en-us/library/windows/desktop/ms724211
            cls.CloseHandle = ctypes.windll.kernel32.CloseHandle
            cls.CloseHandle.argtypes = [HANDLE]
            cls.CloseHandle.restype = BOOL

            class FILETIME(ctypes.Structure):
                _fields_ = [("dwLowDateTime", DWORD),
                            ("dwHighDateTime", DWORD)]

            class BY_HANDLE_FILE_INFORMATION(ctypes.Structure):
                _fields_ = [("dwFileAttributes", DWORD),
                            ("ftCreationTime", FILETIME),
                            ("ftLastAccessTime", FILETIME),
                            ("ftLastWriteTime", FILETIME),
                            ("dwVolumeSerialNumber", DWORD),
                            ("nFileSizeHigh", DWORD),
                            ("nFileSizeLow", DWORD),
                            ("nNumberOfLinks", DWORD),
                            ("nFileIndexHigh", DWORD),
                            ("nFileIndexLow", DWORD)]
            cls.BY_HANDLE_FILE_INFORMATION = BY_HANDLE_FILE_INFORMATION

            # http://msdn.microsoft.com/en-us/library/windows/desktop/aa364952
            cls.GetFileInformationByHandle = ctypes.windll.kernel32.GetFileInformationByHandle
            cls.GetFileInformationByHandle.argtypes = [HANDLE, POINTER(BY_HANDLE_FILE_INFORMATION)]
            cls.GetFileInformationByHandle.restype = BOOL

            cls._st_nlink = cls._windows_st_nlink
