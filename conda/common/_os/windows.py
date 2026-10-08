# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Windows platform helpers."""

from __future__ import annotations

from enum import IntEnum
from logging import getLogger
from typing import TYPE_CHECKING

from ..compat import ensure_binary, on_win

if TYPE_CHECKING:
    from os import PathLike

log = getLogger(__name__)

if on_win:
    from ctypes import (
        POINTER,
        Structure,
        WinDLL,
        WinError,
        byref,
        c_char_p,
        c_int,
        c_ulong,
        c_ulonglong,
        c_void_p,
        c_wchar_p,
        create_string_buffer,
        get_last_error,
        pointer,
        sizeof,
        string_at,
        windll,
    )
    from ctypes.wintypes import BOOL, DWORD, HANDLE, HINSTANCE, HKEY, HWND, WORD

    PHANDLE = POINTER(HANDLE)
    PDWORD = POINTER(DWORD)
    SEE_MASK_NOCLOSEPROCESS = 0x00000040
    INFINITE = -1

    WaitForSingleObject = windll.kernel32.WaitForSingleObject
    WaitForSingleObject.argtypes = (HANDLE, DWORD)
    WaitForSingleObject.restype = DWORD

    CloseHandle = windll.kernel32.CloseHandle
    CloseHandle.argtypes = (HANDLE,)
    CloseHandle.restype = BOOL

    class SECURITY_ATTRIBUTES(Structure):
        _fields_ = (
            ("nLength", DWORD),
            ("lpSecurityDescriptor", c_void_p),
            ("bInheritHandle", BOOL),
        )

    # Keep these function signatures separate from other ctypes users.
    _file_kernel32 = WinDLL("kernel32", use_last_error=True)
    _file_advapi32 = WinDLL("advapi32", use_last_error=True)

    CreateFile = _file_kernel32.CreateFileW
    CreateFile.argtypes = (
        c_wchar_p,
        DWORD,
        DWORD,
        POINTER(SECURITY_ATTRIBUTES),
        DWORD,
        DWORD,
        HANDLE,
    )
    CreateFile.restype = HANDLE

    GetSecurityInfo = _file_advapi32.GetSecurityInfo
    GetSecurityInfo.argtypes = (
        HANDLE,
        DWORD,
        DWORD,
        c_void_p,
        c_void_p,
        c_void_p,
        c_void_p,
        POINTER(c_void_p),
    )
    GetSecurityInfo.restype = DWORD

    GetSecurityDescriptorControl = _file_advapi32.GetSecurityDescriptorControl
    GetSecurityDescriptorControl.argtypes = (c_void_p, POINTER(WORD), PDWORD)
    GetSecurityDescriptorControl.restype = BOOL

    GetSecurityDescriptorDacl = _file_advapi32.GetSecurityDescriptorDacl
    GetSecurityDescriptorDacl.argtypes = (
        c_void_p,
        POINTER(BOOL),
        POINTER(c_void_p),
        POINTER(BOOL),
    )
    GetSecurityDescriptorDacl.restype = BOOL

    GetSecurityDescriptorSacl = _file_advapi32.GetSecurityDescriptorSacl
    GetSecurityDescriptorSacl.argtypes = GetSecurityDescriptorDacl.argtypes
    GetSecurityDescriptorSacl.restype = BOOL

    SetSecurityInfo = _file_advapi32.SetSecurityInfo
    SetSecurityInfo.argtypes = (
        HANDLE,
        DWORD,
        DWORD,
        c_void_p,
        c_void_p,
        c_void_p,
        c_void_p,
    )
    SetSecurityInfo.restype = DWORD

    GetSecurityDescriptorLength = _file_advapi32.GetSecurityDescriptorLength
    GetSecurityDescriptorLength.argtypes = (c_void_p,)
    GetSecurityDescriptorLength.restype = DWORD

    ConvertSecurityDescriptorToStringSecurityDescriptor = (
        _file_advapi32.ConvertSecurityDescriptorToStringSecurityDescriptorW
    )
    ConvertSecurityDescriptorToStringSecurityDescriptor.argtypes = (
        c_void_p,
        DWORD,
        DWORD,
        POINTER(c_wchar_p),
        PDWORD,
    )
    ConvertSecurityDescriptorToStringSecurityDescriptor.restype = BOOL

    ConvertStringSecurityDescriptorToSecurityDescriptor = (
        _file_advapi32.ConvertStringSecurityDescriptorToSecurityDescriptorW
    )
    ConvertStringSecurityDescriptorToSecurityDescriptor.argtypes = (
        c_wchar_p,
        DWORD,
        POINTER(c_void_p),
        PDWORD,
    )
    ConvertStringSecurityDescriptorToSecurityDescriptor.restype = BOOL

    LocalFree = _file_kernel32.LocalFree
    LocalFree.argtypes = (c_void_p,)
    LocalFree.restype = c_void_p

    DuplicateEncryptionInfoFile = _file_advapi32.DuplicateEncryptionInfoFile
    DuplicateEncryptionInfoFile.argtypes = (
        c_wchar_p,
        c_wchar_p,
        DWORD,
        DWORD,
        POINTER(SECURITY_ATTRIBUTES),
    )
    DuplicateEncryptionInfoFile.restype = DWORD

    class ShellExecuteInfo(Structure):
        """
        https://docs.microsoft.com/en-us/windows/desktop/api/shellapi/nf-shellapi-shellexecuteexa
        https://docs.microsoft.com/en-us/windows/desktop/api/shellapi/ns-shellapi-_shellexecuteinfoa
        """

        _fields_ = [
            ("cbSize", DWORD),
            ("fMask", c_ulong),
            ("hwnd", HWND),
            ("lpVerb", c_char_p),
            ("lpFile", c_char_p),
            ("lpParameters", c_char_p),
            ("lpDirectory", c_char_p),
            ("nShow", c_int),
            ("hInstApp", HINSTANCE),
            ("lpIDList", c_void_p),
            ("lpClass", c_char_p),
            ("hKeyClass", HKEY),
            ("dwHotKey", DWORD),
            ("hIcon", HANDLE),
            ("hProcess", HANDLE),
        ]

        def __init__(self, **kwargs):
            Structure.__init__(self)
            self.cbSize = sizeof(self)
            for field_name, field_value in kwargs.items():
                if isinstance(field_value, str):
                    field_value = ensure_binary(field_value)
                setattr(self, field_name, field_value)

    PShellExecuteInfo = POINTER(ShellExecuteInfo)
    ShellExecuteEx = windll.Shell32.ShellExecuteExA
    ShellExecuteEx.argtypes = (PShellExecuteInfo,)
    ShellExecuteEx.restype = BOOL


class SW(IntEnum):
    HIDE = 0
    MAXIMIZE = 3
    MINIMIZE = 6
    RESTORE = 9
    SHOW = 5
    SHOWDEFAULT = 10
    SHOWMAXIMIZED = 3
    SHOWMINIMIZED = 2
    SHOWMINNOACTIVE = 7
    SHOWNA = 8
    SHOWNOACTIVATE = 4
    SHOWNORMAL = 1


class ERROR(IntEnum):
    ZERO = 0
    FILE_NOT_FOUND = 2
    PATH_NOT_FOUND = 3
    BAD_FORMAT = 11
    ACCESS_DENIED = 5
    ASSOC_INCOMPLETE = 27
    DDE_BUSY = 30
    DDE_FAIL = 29
    DDE_TIMEOUT = 28
    DLL_NOT_FOUND = 32
    NO_ASSOC = 31
    OOM = 8
    SHARE = 26


def get_file_security(fd: int) -> bytes:
    """Read ownership, DACL, integrity label, resource attributes, and policy."""
    from msvcrt import get_osfhandle

    descriptor = c_void_p()
    sddl = c_wchar_p()
    normalized = c_void_p()
    # SE_FILE_OBJECT and OWNER | GROUP | DACL | LABEL | ATTRIBUTE | SCOPE
    # SECURITY_INFORMATION. These queries require READ_CONTROL, not audit access.
    error = GetSecurityInfo(
        get_osfhandle(fd), 1, 0x77, None, None, None, None, byref(descriptor)
    )
    if error:
        raise WinError(error)
    try:
        # Native SDDL removes layout and defaulted-flag differences while
        # retaining ordered ACEs and ACL protection and inheritance flags.
        # Use the same query flags so labels and resource attributes survive.
        if not ConvertSecurityDescriptorToStringSecurityDescriptor(
            descriptor, 1, 0x77, byref(sddl), None
        ):
            raise WinError(get_last_error())
        if not ConvertStringSecurityDescriptorToSecurityDescriptor(
            sddl, 1, byref(normalized), None
        ):
            raise WinError(get_last_error())
        return string_at(normalized, GetSecurityDescriptorLength(normalized))
    finally:
        LocalFree(normalized)
        LocalFree(sddl)
        LocalFree(descriptor)


def create_file_with_security(
    path: str | PathLike[str],
    security: bytes,
    *,
    encrypted_source: str | PathLike[str] | None = None,
) -> int:
    """Create an empty protected file and return a descriptor owned by the caller.

    Apply and verify security before any content is written.
    EFS metadata is copied from ``encrypted_source`` when supplied. Audit ACEs
    are not copied. The caller must provide a trusted containing directory.
    """
    import os
    from ctypes import cast
    from msvcrt import open_osfhandle
    from pathlib import Path
    from stat import FILE_ATTRIBUTE_ENCRYPTED

    path = Path(path)
    descriptor = create_string_buffer(security)
    control = WORD()
    revision = DWORD()
    if not GetSecurityDescriptorControl(descriptor, byref(control), byref(revision)):
        raise WinError(get_last_error())
    dacl, sacl = c_void_p(), c_void_p()
    present, defaulted = BOOL(), BOOL()
    if not (
        GetSecurityDescriptorDacl(
            descriptor, byref(present), byref(dacl), byref(defaulted)
        )
        and GetSecurityDescriptorSacl(
            descriptor, byref(present), byref(sacl), byref(defaulted)
        )
    ):
        raise WinError(get_last_error())
    creation = descriptor
    if sacl.value:
        # CreateFile requires audit privileges for a SACL, even for a label.
        # Supply owner, group, and DACL now, then apply the label separately.
        sddl, without_sacl = c_wchar_p(), c_void_p()
        try:
            if not ConvertSecurityDescriptorToStringSecurityDescriptor(
                descriptor, 1, 0x7, byref(sddl), None
            ) or not ConvertStringSecurityDescriptorToSecurityDescriptor(
                sddl, 1, byref(without_sacl), None
            ):
                raise WinError(get_last_error())
            creation = create_string_buffer(
                string_at(without_sacl, GetSecurityDescriptorLength(without_sacl))
            )
        finally:
            LocalFree(without_sacl)
            LocalFree(sddl)
    attributes = SECURITY_ATTRIBUTES(
        sizeof(SECURITY_ATTRIBUTES), cast(creation, c_void_p), False
    )
    # LABEL | ATTRIBUTE, plus DACL and its protection flag when the source
    # uses automatic inheritance. SetSecurityInfo otherwise adds that flag.
    security_info = 0x30 if sacl.value else 0
    if control.value & 0x400:
        security_info |= 0x4 | (0x80000000 if control.value & 0x1000 else 0x20000000)
    # GENERIC_WRITE | READ_CONTROL, plus WRITE_DAC/WRITE_OWNER as needed.
    access = (
        0x40020000 | (0x40000 if security_info else 0) | (0x80000 if sacl.value else 0)
    )
    # No sharing, CREATE_NEW. Verify all security before writing any content.
    handle = CreateFile(str(path), access, 0, byref(attributes), 1, 0, None)
    if handle == c_void_p(-1).value:
        raise WinError(get_last_error())
    try:
        if encrypted_source is not None:
            # EFS needs exclusive access. This file is still empty, and we own
            # it because CREATE_NEW succeeded. CREATE_ALWAYS applies only here.
            if not CloseHandle(handle):
                raise WinError()
            handle = None
            error = DuplicateEncryptionInfoFile(
                os.fspath(encrypted_source), str(path), 2, 0, byref(attributes)
            )
            if error:
                raise WinError(error)
            handle = CreateFile(str(path), access, 0, None, 3, 0, None)
            if handle == c_void_p(-1).value:
                handle = None
                raise WinError(get_last_error())

        if security_info:
            error = SetSecurityInfo(handle, 1, security_info, None, None, dacl, sacl)
            if error:
                raise WinError(error)

        fd = open_osfhandle(handle, os.O_WRONLY | os.O_BINARY | os.O_NOINHERIT)
        handle = None
        try:
            if get_file_security(fd) != security:
                raise OSError("Windows could not preserve file security or inheritance")
            if encrypted_source is not None and not (
                os.fstat(fd).st_file_attributes & FILE_ATTRIBUTE_ENCRYPTED
            ):
                raise OSError("Windows could not preserve file encryption")
        except BaseException:
            os.close(fd)
            raise
        return fd
    except BaseException:
        if handle is not None:
            CloseHandle(handle)
        path.unlink()
        raise


def get_free_space_on_windows(dir_name):
    result = None
    free_bytes = c_ulonglong(0)
    try:
        windll.kernel32.GetDiskFreeSpaceExW(
            c_wchar_p(dir_name),
            None,
            None,
            pointer(free_bytes),
        )
        result = free_bytes.value
    except Exception as e:
        log.info("%r", e)
    return result


def is_admin_on_windows():  # pragma: unix no cover
    # http://stackoverflow.com/a/1026626/2127762
    result = False
    try:
        result = windll.shell32.IsUserAnAdmin() != 0
    except Exception as e:  # pragma: no cover
        log.info("%r", e)
        # result = 'unknown'
    return result


def _wait_and_close_handle(process_handle):
    """Waits until spawned process finishes and closes the handle for it."""
    try:
        WaitForSingleObject(process_handle, INFINITE)
        CloseHandle(process_handle)
    except Exception as e:
        log.info("%r", e)


def run_as_admin(args, wait=True):
    """
    Run command line argument list (`args`) with elevated privileges.

    If `wait` is True, the process will block until completion.

    NOTES:
        - no stdin / stdout / stderr pipe support
        - does not automatically quote arguments (i.e. for paths that may contain spaces)
    See:
    - http://stackoverflow.com/a/19719292/1170370 on 20160407 MCS.
    - msdn.microsoft.com/en-us/library/windows/desktop/bb762153(v=vs.85).aspx
    - https://github.com/ContinuumIO/menuinst/blob/master/menuinst/windows/win_elevate.py
    - https://github.com/saltstack/salt-windows-install/blob/master/deps/salt/python/App/Lib/site-packages/win32/Demos/pipes/runproc.py  # NOQA
    - https://github.com/twonds/twisted/blob/master/twisted/internet/_dumbwin32proc.py
    - https://stackoverflow.com/a/19982092/2127762
    - https://www.codeproject.com/Articles/19165/Vista-UAC-The-Definitive-Guide
    - https://github.com/JustAMan/pyWinClobber/blob/master/win32elevate.py
    """
    arg0 = args[0]
    param_str = " ".join(args[1:] if len(args) > 1 else ())
    hprocess = None
    error_code = None
    try:
        execute_info = ShellExecuteInfo(
            fMask=SEE_MASK_NOCLOSEPROCESS,
            hwnd=None,
            lpVerb="runas",
            lpFile=arg0,
            lpParameters=param_str,
            lpDirectory=None,
            nShow=SW.HIDE,
        )
        successful = ShellExecuteEx(byref(execute_info))
        hprocess = execute_info.hProcess
    except Exception as e:
        successful = False
        error_code = e
        log.info("%r", e)

    if not successful:
        error_code = WinError()
    elif wait:
        _wait_and_close_handle(execute_info.hProcess)

    return hprocess, error_code
