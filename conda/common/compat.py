# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from os import lstat
import os
from logging import getLogger

from .._vendor.auxlib.compat import (iteritems, with_metaclass, itervalues,  # NOQA
                                     string_types, primitive_types, text_type, odict,  # NOQA
                                     StringIO, isiterable)  # NOQA

from ..compat import *  # NOQA

log = getLogger(__name__)


def ensure_binary(value):
    return value.encode('utf-8') if hasattr(value, 'encode') else value


def ensure_text_type(value):
    return value.decode('utf-8') if hasattr(value, 'decode') else value


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
        if os.name != 'nt':
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
