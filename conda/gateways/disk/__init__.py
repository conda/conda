# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from errno import EACCES, EEXIST, EIO, ENOENT, ENOTEMPTY, EPERM, errorcode
import gc
from logging import getLogger
import os
from os import makedirs, mkdir
from os.path import basename, dirname, isdir
from random import random
import sys
from time import sleep

from ...common.compat import on_win

log = getLogger(__name__)

# EACCES:    Permission denied
# EEXIST:    File exists
# EIO:       I/O error
# ENOENT:    No such file or directory
# ENOTEMPTY: Directory not empty
# EPERM:     Operation not permitted
# Windows:   https://msdn.microsoft.com/en-us/library/5814770t.aspx

# without the time cap:
#   MAX_TRIES = 5, max total time ~= 3.1 sec
#   MAX_TRIES = 6, max total time ~= 6.3 sec   sum(0.1 * 2 ** n for n in range(6))
#   MAX_TRIES = 7, max total time ~= 12.7 sec
#
# with MAX_SLEEP_CAP at 5:
#   MAX_TRIES = 5, max total time ~= 3.1 sec
#   MAX_TRIES = 6, max total time ~= 6.3 sec    sum(0.1 * 2 ** min((n, 5)) for n in range(6))
#   MAX_TRIES = 7, max total time ~= 9.5 sec    sum(0.1 * 2 ** min((n, 5)) for n in range(7))
#   MAX_TRIES = 8, max total time ~= 12.7 sec   sum(0.1 * 2 ** min((n, 5)) for n in range(8))
#   MAX_TRIES = 10, max total time ~= 19.1 sec  sum(0.1 * 2 ** min((n, 5)) for n in range(10))
MAX_TRIES = 8
MAX_SLEEP_CAP = 5  # ~3.2 sec max sleep


def exp_backoff_fn(fn, *args, **kwargs):
    """Mostly for retrying file operations that fail on Windows due to virus scanners"""
    max_tries = kwargs.pop('max_tries', MAX_TRIES)
    if not on_win:
        return fn(*args, **kwargs)

    for n in range(max_tries):
        try:
            result = fn(*args, **kwargs)
        except EnvironmentError as e:
            log.trace(repr(e))
            if e.errno in (EACCES, EPERM, EIO):
                if n == max_tries-1:
                    raise
                sleep_time = (2 ** min(n, MAX_SLEEP_CAP) + random()) * 0.1
                caller_frame = sys._getframe(1)
                log.debug("retrying %s/%s %s() in %g sec",
                          basename(caller_frame.f_code.co_filename),
                          caller_frame.f_lineno,
                          fn.__name__,
                          sleep_time)
                sleep(sleep_time)
                if n > 3:
                    gc.collect()
            elif e.errno in (ENOENT, ENOTEMPTY):
                # errno.ENOENT File not found error / No such file or directory
                # errno.ENOTEMPTY OSError(41, 'The directory is not empty')
                raise
            else:
                log.warn("Uncaught backoff with errno %s %d", errorcode[e.errno], e.errno)
                raise
        else:
            return result


def mkdir_p(path):
    # putting this here to help with circular imports
    try:
        log.trace('making directory %s', path)
        if path:
            makedirs(path)
            return isdir(path) and path
    except OSError as e:
        if e.errno == EEXIST and isdir(path):
            return path
        else:
            raise


def mkdir_p_sudo_safe(path):
    if isdir(path):
        return
    base_dir = dirname(path)
    if not isdir(base_dir):
        mkdir_p_sudo_safe(base_dir)
    log.trace('making directory %s', path)
    mkdir(path)
    if not on_win and os.environ.get('SUDO_UID') is not None:
        uid = int(os.environ['SUDO_UID'])
        gid = int(os.environ.get('SUDO_GID', -1))
        log.trace("chowning %s:%s %s", uid, gid, path)
        os.chown(path, uid, gid)
