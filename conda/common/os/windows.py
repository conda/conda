# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import absolute_import, division, print_function, unicode_literals

from enum import IntEnum
from logging import getLogger

from ..compat import on_win


_ctypes = None
if on_win:
    import ctypes as _ctypes


log = getLogger(__name__)


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


def get_free_space_on_windows(dir_name):
    result = None
    if _ctypes:
        free_bytes = _ctypes.c_ulonglong(0)
        _ctypes.windll.kernel32.GetDiskFreeSpaceExW(_ctypes.c_wchar_p(dir_name), None,
                                                    None, _ctypes.pointer(free_bytes))
        result = free_bytes.value

    return result


def is_admin_on_windows():  # pragma: unix no cover
    # http://stackoverflow.com/a/1026626/2127762
    result = False
    if _ctypes:
        try:
            result = _ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception as e:  # pragma: no cover
            log.info('%r', e)
            result = 'unknown'

    return result


def run_as_admin(args):
    """
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
    """
    hinstance = None
    error_code = None
    if _ctypes:
        arg0 = args[0]
        param_str = ' '.join(args[1:] if len(args) > 1 else ())
        hinstance_or_code = _ctypes.windll.shell32.ShellExecuteW(
            None, 'runas', arg0, param_str, None, SW.HIDE
        )

        if hinstance_or_code <= 32:
            error_code = hinstance_or_code
        else:
            hinstance = hinstance_or_code

    return hinstance, error_code
