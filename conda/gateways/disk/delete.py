# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from errno import ENOENT
from logging import getLogger
from os import listdir, removedirs, rename, unlink, walk
from os.path import abspath, dirname, isdir, join
from shutil import rmtree as shutil_rmtree
from uuid import uuid4

from . import MAX_TRIES, exp_backoff_fn
from .link import islink, lexists
from .permissions import make_writable, recursive_make_writable
from ...base.context import context
from ...common.compat import PY2, on_win, text_type, ensure_binary

log = getLogger(__name__)


def rm_rf(path, max_retries=5, trash=True):
    """
    Completely delete path
    max_retries is the number of times to retry on failure. The default is 5. This only applies
    to deleting a directory.
    If removing path fails and trash is True, files will be moved to the trash directory.
    """
    try:
        path = abspath(path)
        log.trace("rm_rf %s", path)
        if isdir(path) and not islink(path):
            # On Windows, always move to trash first.
            if trash and on_win:
                move_result = move_path_to_trash(path, preclean=False)
                if move_result:
                    return True
            backoff_rmdir(path)
        elif lexists(path):
            try:
                backoff_unlink(path)
                return True
            except (OSError, IOError) as e:
                log.debug("%r errno %d\nCannot unlink %s.", e, e.errno, path)
                if trash:
                    move_result = move_path_to_trash(path)
                    if move_result:
                        return True
                log.info("Failed to remove %s.", path)
        else:
            log.trace("rm_rf failed. Not a link, file, or directory: %s", path)
        return True
    finally:
        if lexists(path):
            log.info("rm_rf failed for %s", path)
            return False


def delete_trash(prefix=None):
    for pkg_dir in context.pkgs_dirs:
        trash_dir = join(pkg_dir, '.trash')
        if not lexists(trash_dir):
            log.trace("Trash directory %s doesn't exist. Moving on.", trash_dir)
            continue
        log.trace("removing trash for %s", trash_dir)
        for p in listdir(trash_dir):
            path = join(trash_dir, p)
            try:
                if isdir(path):
                    backoff_rmdir(path, max_tries=1)
                else:
                    backoff_unlink(path, max_tries=1)
            except (IOError, OSError) as e:
                log.info("Could not delete path in trash dir %s\n%r", path, e)
        files_remaining = listdir(trash_dir)
        if files_remaining:
            log.info("Unable to fully clean trash directory %s\nThere are %d remaining file(s).",
                     trash_dir, len(files_remaining))


def move_to_trash(prefix, f, tempdir=None):
    """
    Move a file or folder f from prefix to the trash

    tempdir is a deprecated parameter, and will be ignored.

    This function is deprecated in favor of `move_path_to_trash`.
    """
    return move_path_to_trash(join(prefix, f) if f else prefix)


def move_path_to_trash(path, preclean=True):
    trash_file = join(context.trash_dir, text_type(uuid4()))
    try:
        rename(path, trash_file)
    except (IOError, OSError) as e:
        log.trace("Could not move %s to %s.\n%r", path, trash_file, e)
        return False
    else:
        log.trace("Moved to trash: %s", path)
        return True


def backoff_unlink(file_or_symlink_path, max_tries=MAX_TRIES):
    def _unlink(path):
        make_writable(path)
        unlink(path)

    try:
        exp_backoff_fn(lambda f: lexists(f) and _unlink(f), file_or_symlink_path,
                       max_tries=max_tries)
    except (IOError, OSError) as e:
        if e.errno not in (ENOENT,):
            # errno.ENOENT File not found error / No such file or directory
            raise


def backoff_rmdir(dirpath, max_tries=MAX_TRIES):
    if not isdir(dirpath):
        return

    # shutil.rmtree:
    #   if onerror is set, it is called to handle the error with arguments (func, path, exc_info)
    #     where func is os.listdir, os.remove, or os.rmdir;
    #     path is the argument to that function that caused it to fail; and
    #     exc_info is a tuple returned by sys.exc_info() ==> (type, value, traceback).
    def retry(func, path, exc_info):
        if getattr(exc_info[1], 'errno', None) == ENOENT:
            return
        recursive_make_writable(dirname(path), max_tries=max_tries)
        func(path)

    def _rmdir(path):
        try:
            recursive_make_writable(path)
            exp_backoff_fn(rmtree, path, onerror=retry, max_tries=max_tries)
        except (IOError, OSError) as e:
            if e.errno == ENOENT:
                log.trace("no such file or directory: %s", path)
            else:
                raise

    for root, dirs, files in walk(dirpath, topdown=False):
        for file in files:
            backoff_unlink(join(root, file), max_tries=max_tries)
        for dir in dirs:
            _rmdir(join(root, dir))

    _rmdir(dirpath)


def try_rmdir_all_empty(dirpath, max_tries=MAX_TRIES):
    if not dirpath or not isdir(dirpath):
        return

    try:
        log.trace("Attempting to remove directory %s", dirpath)
        exp_backoff_fn(removedirs, dirpath, max_tries=max_tries)
    except (IOError, OSError) as e:
        # this function only guarantees trying, so we just swallow errors
        log.trace('%r', e)


if not (on_win and PY2):
    rmtree = shutil_rmtree
else:  # pragma: no cover
    # adapted from http://code.activestate.com/recipes/578849-reimplementation-of-rmtree-supporting-windows-repa/  # NOQA
    # revision #3 http://code.activestate.com/recipes/578849-reimplementation-of-rmtree-supporting-windows-repa/history/3/  # NOQA
    # licensed under the CC0 License 1.0 ("Public Domain")

    # TODO: this code should probably be unified with the jaraco code in conda.gateways.disk.link

    from ctypes import (Structure, byref, WinDLL, c_int, c_ubyte, c_ssize_t, _SimpleCData,
                        cast, sizeof, WinError, POINTER as _POINTER)
    from ctypes.wintypes import DWORD, INT, LPWSTR, LONG, WORD, BYTE
    from os import rmdir
    import sys

    if PY2:
        _long = long  # NOQA
    else:
        _long = int  # lgtm [py/unreachable-statement]

    def rmtree(filepath, ignore_errors=False, onerror=None):
        """
        Re-implementation of shutil.rmtree that checks for reparse points
        (junctions/symbolic links) before iterating folders.
        """

        def rm(fn, childpath):
            try:
                fn(childpath)
            except:
                if not ignore_errors:
                    if onerror is None:
                        raise
                    else:
                        onerror(fn, childpath, sys.exc_info()[0])

        def visit_files(root, targets):
            for target in targets:
                rm(unlink, join(root, target))

        def visit_dirs(root, targets):
            for target in targets:
                childpath = join(root, target)
                rmtree(childpath, ignore_errors, onerror)

        if is_reparse_point(filepath):
            rm(delete_reparse_point, filepath)
            return

        for root, dirs, files in walk(filepath):
            visit_files(root, files)
            visit_dirs(root, dirs)

        rm(rmdir, filepath)

    # Some utility wrappers for pointer stuff.
    class c_void(Structure):
        # c_void_p is a buggy return type, converting to int, so
        # POINTER(None) == c_void_p is actually written as
        # POINTER(c_void), so it can be treated as a real pointer.
        _fields_ = [(ensure_binary('dummy'), c_int)]

        def __init__(self, value=None):
            if value is None:
                value = 0
            super(c_void, self).__init__(value)

    def POINTER(obj):
        ptr = _POINTER(obj)
        # Convert None to a real NULL pointer to work around bugs
        # in how ctypes handles None on 64-bit platforms
        if not isinstance(ptr.from_param, classmethod):
            def from_param(cls, x):
                if x is None:
                    return cls()
                return x

            ptr.from_param = classmethod(from_param)
        return ptr

    # Shadow built-in c_void_p
    LPVOID = c_void_p = POINTER(c_void)

    # Globals
    NULL = LPVOID()
    kernel32 = WinDLL(ensure_binary('kernel32'))
    advapi32 = WinDLL(ensure_binary('advapi32'))
    _obtained_privileges = []

    # Aliases to functions/classes, and utility lambdas
    cast = cast
    byref = byref
    sizeof = sizeof
    WinError = WinError
    hasflag = lambda value, flag: (value & flag) == flag

    # Constants derived from C
    INVALID_HANDLE_VALUE = -1

    # Desired access for OpenProcessToken
    TOKEN_ADJUST_PRIVILEGES = 0x0020

    # SE Privilege Names
    SE_RESTORE_NAME = ensure_binary('SeRestorePrivilege')
    SE_BACKUP_NAME = ensure_binary('SeBackupPrivilege')

    # SE Privilege Attributes
    SE_PRIVILEGE_ENABLED = _long(0x00000002)

    # Access
    FILE_ANY_ACCESS = 0

    # CreateFile flags
    FILE_FLAG_BACKUP_SEMANTICS = 0x02000000
    FILE_FLAG_OPEN_REPARSE_POINT = 0x00200000

    # Generic access
    GENERIC_READ = _long(0x80000000)  # NOQA
    GENERIC_WRITE = _long(0x40000000)  # NOQA
    GENERIC_RW = GENERIC_READ | GENERIC_WRITE

    # File shared access
    FILE_SHARE_READ = 0x00000001
    FILE_SHARE_WRITE = 0x00000002
    FILE_SHARE_DELETE = 0x00000004
    FILE_SHARE_ALL = FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE

    # File stuff
    OPEN_EXISTING = 3
    FILE_ATTRIBUTE_REPARSE_POINT = 0x00000400
    FILE_DEVICE_FILE_SYSTEM = 0x00000009

    # Utility lambdas for figuring out ctl codes
    CTL_CODE = lambda devtype, func, meth, acc: (devtype << 16) | (acc << 14) | (func << 2) | meth

    # Methods
    METHOD_BUFFERED = 0

    # WinIoCtl Codes
    FSCTL_GET_REPARSE_POINT = CTL_CODE(FILE_DEVICE_FILE_SYSTEM, 42, METHOD_BUFFERED,
                                       FILE_ANY_ACCESS)
    FSCTL_DELETE_REPARSE_POINT = CTL_CODE(FILE_DEVICE_FILE_SYSTEM, 43, METHOD_BUFFERED,
                                          FILE_ANY_ACCESS)

    # Reparse Point buffer constants
    MAX_NAME_LENGTH = 1024
    MAX_REPARSE_BUFFER = 16 * MAX_NAME_LENGTH
    REPARSE_GUID_DATA_BUFFER_HEADER_SIZE = (2 * sizeof(WORD)) + (sizeof(DWORD) * 5)

    # For our generic reparse buffer
    MAX_GENERIC_REPARSE_BUFFER = MAX_REPARSE_BUFFER - REPARSE_GUID_DATA_BUFFER_HEADER_SIZE

    # Type aliases
    UCHAR = c_ubyte
    ULONG_PTR = c_ssize_t
    LPDWORD = POINTER(DWORD)

    # CTypes-based wrapper classes
    class BOOL(INT):
        """
        Wrapper around ctypes.wintypes.INT (ctypes.c_int) to make BOOL act a bit more like
        a boolean.
        """

        @classmethod
        def from_param(cls, value):
            if isinstance(value, _SimpleCData):
                return BOOL(value.value)
            elif not value or value is None:
                return BOOL(0)
            else:
                raise TypeError('Dont know what to do with instance of {0}'.format(type(value)))

        def __eq__(self, other):
            value = bool(self.value)
            if isinstance(other, bool):
                return value and other
            elif isinstance(other, _SimpleCData):
                return value and bool(other.value)
            else:
                return value and bool(other)

        def __hash__(self):
            return hash(self._as_parameter_)

    class HANDLE(ULONG_PTR):
        """
        Wrapper around the numerical representation of a pointer to
        add checks for INVALID_HANDLE_VALUE
        """
        NULL = None
        INVALID = None

        def __init__(self, value=None):
            if value is None:
                value = 0
            super(HANDLE, self).__init__(value)
            self.autoclose = False

        @classmethod
        def from_param(cls, value):
            if value is None:
                return HANDLE(0)
            elif isinstance(value, _SimpleCData):
                return value
            else:
                return HANDLE(value)

        def close(self):
            if bool(self):
                try:
                    CloseHandle(self)
                except:
                    pass

        def __enter__(self):
            self.autoclose = True
            return self

        def __exit__(self, exc_typ, exc_val, trace):
            self.close()
            return False

        def __del__(self):
            if hasattr(self, 'autoclose') and self.autoclose:
                CloseHandle(self)

        def __nonzero__(self):
            return super(HANDLE, self).__nonzero__() and self.value != HANDLE.INVALID.value

    class GUID(Structure):
        """ Borrowed small parts of this from the comtypes module. """
        _fields_ = [
            (ensure_binary('Data1'), DWORD),
            (ensure_binary('Data2'), WORD),
            (ensure_binary('Data3'), WORD),
            (ensure_binary('Data4'), (BYTE * 8)),
        ]

    # Ctypes Structures
    class LUID(Structure):
        _fields_ = [
            (ensure_binary('LowPart'), DWORD),
            (ensure_binary('HighPart'), LONG),
        ]

    class LUID_AND_ATTRIBUTES(LUID):
        _fields_ = [(ensure_binary('Attributes'), DWORD)]

    class GenericReparseBuffer(Structure):
        _fields_ = [(ensure_binary('PathBuffer'), UCHAR * MAX_GENERIC_REPARSE_BUFFER)]

    class ReparsePoint(Structure):
        """
        Originally, Buffer was a union made up of SymbolicLinkBuffer, MountpointBuffer,
        and GenericReparseBuffer. Since we're not actually doing anything with the buffer
        aside from passing it along to the native functions, however, I've gone ahead
        and cleaned up some of of the unnecessary code.
        """

        _fields_ = [
            (ensure_binary('ReparseTag'), DWORD),
            (ensure_binary('ReparseDataLength'), WORD),
            (ensure_binary('Reserved'), WORD),
            (ensure_binary('ReparseGuid'), GUID),
            (ensure_binary('Buffer'), GenericReparseBuffer)
        ]

    # Common uses of HANDLE
    HANDLE.NULL = HANDLE()
    HANDLE.INVALID = HANDLE(INVALID_HANDLE_VALUE)
    LPHANDLE = POINTER(HANDLE)

    # C Function Prototypes
    CreateFile = kernel32.CreateFileW
    CreateFile.restype = HANDLE
    CreateFile.argtypes = [LPWSTR, DWORD, DWORD, LPVOID, DWORD, DWORD, HANDLE]

    GetFileAttributes = kernel32.GetFileAttributesW
    GetFileAttributes.restype = DWORD
    GetFileAttributes.argtypes = [LPWSTR]

    RemoveDirectory = kernel32.RemoveDirectoryW
    RemoveDirectory.restype = BOOL
    RemoveDirectory.argtypes = [LPWSTR]

    CloseHandle = kernel32.CloseHandle
    CloseHandle.restype = BOOL
    CloseHandle.argtypes = [HANDLE]

    GetCurrentProcess = kernel32.GetCurrentProcess
    GetCurrentProcess.restype = HANDLE
    GetCurrentProcess.argtypes = []

    OpenProcessToken = advapi32.OpenProcessToken
    OpenProcessToken.restype = BOOL
    OpenProcessToken.argtypes = [HANDLE, DWORD, LPHANDLE]

    LookupPrivilegeValue = advapi32.LookupPrivilegeValueW
    LookupPrivilegeValue.restype = BOOL
    LookupPrivilegeValue.argtypes = [LPWSTR, LPWSTR, POINTER(LUID_AND_ATTRIBUTES)]

    AdjustTokenPrivileges = advapi32.AdjustTokenPrivileges
    AdjustTokenPrivileges.restype = BOOL
    AdjustTokenPrivileges.argtypes = [HANDLE, BOOL, LPVOID, DWORD, LPVOID, LPDWORD]

    _DeviceIoControl = kernel32.DeviceIoControl
    _DeviceIoControl.restype = BOOL
    _DeviceIoControl.argtypes = [HANDLE, DWORD, LPVOID, DWORD, LPVOID, DWORD, LPDWORD, LPVOID]

    def DeviceIoControl(hDevice, dwCtrlCode, lpIn, szIn, lpOut, szOut, lpOverlapped=None):
        """
        Wrapper around the real DeviceIoControl to return a tuple containing a bool indicating
        success, and a number containing the size of the bytes returned. (Also, lpOverlapped to
        default to NULL) """
        dwRet = DWORD(0)
        return bool(
            _DeviceIoControl(hDevice, dwCtrlCode, lpIn, szIn, lpOut, szOut, byref(dwRet),
                             lpOverlapped)
        ), dwRet.value

    def obtain_privileges(privileges):
        """
        Given a list of SE privilege names (eg: [ SE_CREATE_TOKEN_NAME, SE_BACKUP_NAME ]), lookup
        the privilege values for each and then attempt to acquire them for the current process.
        """
        global _obtained_privileges
        privileges = filter(lambda priv: priv not in _obtained_privileges, list(set(privileges)))
        privcount = len(privileges)
        if privcount == 0:
            return

        class TOKEN_PRIVILEGES(Structure):
            # noinspection PyTypeChecker
            _fields_ = [
                (ensure_binary('PrivilegeCount'), DWORD),
                (ensure_binary('Privileges'), LUID_AND_ATTRIBUTES * privcount),
            ]

        with HANDLE() as hToken:
            tp = TOKEN_PRIVILEGES()
            tp.PrivilegeCount = privcount
            hProcess = GetCurrentProcess()
            if not OpenProcessToken(hProcess, TOKEN_ADJUST_PRIVILEGES, byref(hToken)):
                raise WinError()

            for i, privilege in enumerate(privileges):
                tp.Privileges[i].Attributes = SE_PRIVILEGE_ENABLED
                if not LookupPrivilegeValue(None, privilege, byref(tp.Privileges[i])):
                    raise Exception('LookupPrivilegeValue failed for privilege: %s' % privilege)

            if not AdjustTokenPrivileges(hToken, False, byref(tp), sizeof(TOKEN_PRIVILEGES), None,
                                         None):
                raise WinError()

            _obtained_privileges.extend(privileges)

    def open_file(filepath, flags=FILE_FLAG_OPEN_REPARSE_POINT, autoclose=False):
        """ Open file for read & write, acquiring the SE_BACKUP & SE_RESTORE privileges. """
        obtain_privileges([SE_BACKUP_NAME, SE_RESTORE_NAME])
        if (flags & FILE_FLAG_BACKUP_SEMANTICS) != FILE_FLAG_BACKUP_SEMANTICS:
            flags |= FILE_FLAG_BACKUP_SEMANTICS
        hFile = CreateFile(filepath, GENERIC_RW, FILE_SHARE_ALL, NULL, OPEN_EXISTING, flags,
                           HANDLE.NULL)
        if not hFile:
            raise WinError()
        if autoclose:
            hFile.autoclose = True
        return hFile

    def get_buffer(filepath, hFile=HANDLE.INVALID):
        """ Get a reparse point buffer. """
        if not hFile:
            hFile = open_file(filepath, autoclose=True)

        obj = ReparsePoint()
        result, dwRet = DeviceIoControl(hFile, FSCTL_GET_REPARSE_POINT, None, _long(0), byref(obj),
                                        MAX_REPARSE_BUFFER)
        return obj if result else None

    def delete_reparse_point(filepath):
        """ Remove the reparse point folder at filepath. """
        dwRet = 0
        with open_file(filepath) as hFile:
            # Try to delete it first without the reparse GUID
            info = ReparsePoint()
            info.ReparseTag = 0
            result, dwRet = DeviceIoControl(hFile, FSCTL_DELETE_REPARSE_POINT, byref(info),
                                            REPARSE_GUID_DATA_BUFFER_HEADER_SIZE, None, _long(0))

            if not result:
                # If the first try fails, we'll set the GUID and try again
                buffer = get_buffer(filepath, hFile)
                info.ReparseTag = buffer.ReparseTag
                info.ReparseGuid = info.ReparseGuid
                result, dwRet = DeviceIoControl(hFile, FSCTL_DELETE_REPARSE_POINT, byref(info),
                                                REPARSE_GUID_DATA_BUFFER_HEADER_SIZE, None,
                                                _long(0))
                if not result:
                    raise WinError()

        if not RemoveDirectory(filepath):
            raise WinError()

        return dwRet

    def is_reparse_point(filepath):
        """ Check whether or not filepath refers to a reparse point. """
        return hasflag(GetFileAttributes(filepath), FILE_ATTRIBUTE_REPARSE_POINT)
