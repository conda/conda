# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import absolute_import, division, print_function, unicode_literals

from errno import ENOENT
import fnmatch
from logging import getLogger
from os import listdir, removedirs, rename, unlink, walk
from os.path import abspath, dirname, isdir, join, split
import shutil
from subprocess import Popen, PIPE
import sys
from uuid import uuid4

from . import MAX_TRIES, exp_backoff_fn
from .link import islink, lexists
from .permissions import make_writable, recursive_make_writable
from ...base.context import context
from ...common.compat import PY2, on_win, text_type, ensure_binary

if on_win:
    import win32file
    import pywintypes


log = getLogger(__name__)


def rmtree(path):
    # subprocessing to delete large folders can be quite a bit faster
    if on_win:
        subprocess.check_call('rd /s /q {}'.format(dirpath), shell=True)
    else:
        try:
            os.makedirs('.empty')
        except:
            pass
        del_dir_cmd = 'rsync -a --delete .empty {}/'
        subprocess.check_call(del_dir_cmd.format(dirpath).split())
        shutil.rmtree('.empty')


def unlink_or_rename_to_trash(path):
    try:
        unlink(path)
    except (OSError, IOError) as e:
        if on_win:

            condabin_dir = join(context.conda_prefix, "condabin")
            trash_script = join(condabin_dir, 'rename_trash.bat')
            p = Popen(['cmd.exe', '/C', trash_script, *split(path)], stdout=PIPE, stderr=PIPE)
            stdout, stderr = p.communicate()
        else:
            rename(path, path + ".trash")


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
            backoff_rmdir(path)
        elif lexists(path):
            unlink_or_rename_to_trash(path)
        else:
            log.trace("rm_rf failed. Not a link, file, or directory: %s", path)
        return True
    finally:
        if lexists(path):
            log.info("rm_rf failed for %s", path)
            return False


def delete_trash(prefix=None):
    if not prefix:
        prefix = sys.prefix
    for root, dirs, files in walk(prefix):
        for basename in files:
            if fnmatch.fnmatch(basename, "*.trash"):
                filename = join(root, basename)
                try:
                    unlink(filename)
                except (OSError, IOError) as e:
                    log.debug("%r errno %d\nCannot unlink %s.", e, e.errno, filename)


def backoff_rmdir(dirpath, max_tries=MAX_TRIES):
    if not isdir(dirpath):
        return

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

    try:
        rmtree(dirpath)
    # we don't really care about errors that much.  We'll catch remaining files
    #    with slower python logic.
    except:
        pass

    for root, dirs, files in walk(dirpath, topdown=False):
        for file in files:
            unlink_or_rename_trash(join(root, file))
        for dir in dirs:
            _rmdir(join(root, dir))

    _rmdir(dirpath)

