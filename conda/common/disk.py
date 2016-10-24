# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import errno
import shutil
import sys
from conda import CondaError
from errno import EACCES, EEXIST, ENOENT, EPERM
from itertools import chain
from logging import getLogger
from os import (W_OK, access, chmod, getpid, link as os_link, listdir, lstat, makedirs, readlink,
                rename, symlink, unlink, walk, stat)
from os.path import abspath, basename, dirname, isdir, isfile, islink, join, lexists
from shutil import rmtree
from stat import S_IEXEC, S_IMODE, S_ISDIR, S_ISLNK, S_ISREG, S_IWRITE
from time import sleep
from uuid import uuid4

from ..compat import lchmod, text_type
from ..exceptions import CondaOSError
from ..utils import on_win

__all__ = ["rm_rf", "exp_backoff_fn", "try_write"]

log = getLogger(__name__)




def conda_bld_ensure_dir(path):
    # this can fail in parallel operation, depending on timing.  Just try to make the dir,
    #    but don't bail if fail.
    if not isdir(path):
        try:
            makedirs(path)
        except OSError:
            pass
