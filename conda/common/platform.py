# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from collections import OrderedDict
import ctypes
from genericpath import exists
from glob import glob
from logging import getLogger
import os
import sys

from .compat import iteritems, on_win
from .._vendor.auxlib.decorators import memoize

log = getLogger(__name__)


def is_admin_on_windows():  # pragma: unix no cover
    # http://stackoverflow.com/a/1026626/2127762
    if not on_win:  # pragma: no cover
        return False
    try:
        from ctypes import windll
        return windll.shell32.IsUserAnAdmin() != 0
    except ImportError as e:  # pragma: no cover
        log.debug('%r', e)
        return 'unknown'
    except Exception as e:  # pragma: no cover
        log.info('%r', e)
        return 'unknown'


def is_admin():
    if on_win:
        return is_admin_on_windows()
    else:
        return os.geteuid() == 0 or os.getegid() == 0


@memoize
def linux_get_libc_version():
    """
    If on linux, returns (libc_family, version), otherwise (None, None)
    """

    if not sys.platform.startswith('linux'):
        return None, None

    from os import confstr, confstr_names, readlink

    # Python 2.7 does not have either of these keys in confstr_names, so provide
    # hard-coded defaults and assert if the key is in confstr_names but differs.
    # These are defined by POSIX anyway so should never change.
    confstr_names_fallback = OrderedDict([('CS_GNU_LIBC_VERSION', 2),
                                          ('CS_GNU_LIBPTHREAD_VERSION', 3)])

    val = None
    for k, v in iteritems(confstr_names_fallback):
        assert k not in confstr_names or confstr_names[k] == v, (
            "confstr_names_fallback for %s is %s yet in confstr_names it is %s"
            "" % (k, confstr_names_fallback[k], confstr_names[k])
        )
        try:
            val = str(confstr(v))
        except:  # pragma: no cover
            pass
        else:
            if val:
                break

    if not val:  # pragma: no cover
        # Weird, play it safe and assume glibc 2.5
        family, version = 'glibc', '2.5'
        log.warning("Failed to detect libc family and version, assuming %s/%s", family, version)
        return family, version
    family, version = val.split(' ')

    # NPTL is just the name of the threading library, even though the
    # version refers to that of uClibc. readlink() can help to try to
    # figure out a better name instead.
    if family == 'NPTL':  # pragma: no cover
        clibs = glob('/lib/libc.so*')
        for clib in clibs:
            clib = readlink(clib)
            if exists(clib):
                if clib.startswith('libuClibc'):
                    if version.startswith('0.'):
                        family = 'uClibc'
                    else:
                        family = 'uClibc-ng'
                    return family, version
        # This could be some other C library; it is unlikely though.
        family = 'uClibc'
        log.warning("Failed to detect non-glibc family, assuming %s (%s)", family, version)
        return family, version
    return family, version


def get_free_space(dir_name):
    """Return folder/drive free space (in bytes).
    :param dir_name: the dir name need to check
    :return: amount of free space

    Examples:
        >>> get_free_space(os.getcwd()) > 0
        True
    """
    if on_win:
        free_bytes = ctypes.c_ulonglong(0)
        ctypes.windll.kernel32.GetDiskFreeSpaceExW(ctypes.c_wchar_p(dir_name), None, None,
                                                   ctypes.pointer(free_bytes))
        return free_bytes.value
    else:
        st = os.statvfs(dir_name)
        return st.f_bavail * st.f_frsize
