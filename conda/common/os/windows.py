# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import absolute_import, division, print_function, unicode_literals

from logging import getLogger

from ...compat import on_win


_ctypes = None
if on_win:
    import ctypes as _ctypes


log = getLogger(__name__)


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
