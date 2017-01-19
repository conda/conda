# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import sys
from errno import EACCES, ENOENT, EPERM, ENOTEMPTY, errorcode
from logging import getLogger
from os.path import basename
from time import sleep

from ...common.compat import on_win

log = getLogger(__name__)

MAX_TRIES = 7


def exp_backoff_fn(fn, *args, **kwargs):
    """Mostly for retrying file operations that fail on Windows due to virus scanners"""
    max_tries = kwargs.pop('max_tries', MAX_TRIES)
    if not on_win:
        return fn(*args, **kwargs)

    import random
    # with max_tries = 6, max total time ~= 3.2 sec
    # with max_tries = 7, max total time ~= 6.5 sec
    for n in range(max_tries):
        try:
            result = fn(*args, **kwargs)
        except (OSError, IOError) as e:
            log.trace(repr(e))
            if e.errno in (EPERM, EACCES):
                if n == max_tries-1:
                    raise
                sleep_time = ((2 ** n) + random.random()) * 0.1
                caller_frame = sys._getframe(1)
                log.trace("retrying %s/%s %s() in %g sec",
                          basename(caller_frame.f_code.co_filename),
                          caller_frame.f_lineno,
                          fn.__name__,
                          sleep_time)
                sleep(sleep_time)
            elif e.errno in (ENOENT, ENOTEMPTY):
                # errno.ENOENT File not found error / No such file or directory
                # errno.ENOTEMPTY OSError(41, 'The directory is not empty')
                raise
            else:
                log.warn("Uncaught backoff with errno %s %d", errorcode[e.errno], e.errno)
                raise
        else:
            return result
