# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from errno import EACCES, ENOENT, EPERM
from itertools import chain
from logging import getLogger
from os import (chmod, lstat, walk)
from os.path import isdir, join
from stat import S_IEXEC, S_IMODE, S_ISDIR, S_ISLNK, S_ISREG, S_IWRITE

from . import exp_backoff_fn
from ...compat import lchmod

log = getLogger(__name__)


def make_writable(path):
    try:
        mode = lstat(path).st_mode
        if S_ISDIR(mode):
            chmod(path, S_IMODE(mode) | S_IWRITE | S_IEXEC)
        elif S_ISREG(mode):
            chmod(path, S_IMODE(mode) | S_IWRITE)
        elif S_ISLNK(mode):
            lchmod(path, S_IMODE(mode) | S_IWRITE)
        else:
            log.debug("path cannot be made writable: %s", path)
    except Exception as e:
        eno = getattr(e, 'errno', None)
        if eno in (ENOENT,):
            log.debug("tried to make writable, but didn't exist: %s", path)
            raise
        elif eno in (EACCES, EPERM):
            log.debug("tried make writable but failed: %s\n%r", path, e)
        else:
            log.warn("Error making path writable: %s\n%r", path, e)
            raise


def recursive_make_writable(path):
    # The need for this function was pointed out at
    #   https://github.com/conda/conda/issues/3266#issuecomment-239241915
    # Especially on windows, file removal will often fail because it is marked read-only
    if isdir(path):
        for root, dirs, files in walk(path):
            for path in chain.from_iterable((files, dirs)):
                try:
                    exp_backoff_fn(make_writable, join(root, path))
                except (IOError, OSError) as e:
                    if e.errno == ENOENT:
                        log.debug("no such file or directory: %s", path)
                    else:
                        raise
    else:
        exp_backoff_fn(make_writable, path)
