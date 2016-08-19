# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import sys
from conda.compat import text_type
from errno import EACCES, EEXIST, ENOENT, EPERM
from itertools import chain
from logging import getLogger
from os import W_OK, access, chmod, getpid, makedirs, rename, stat, unlink, walk
from os.path import basename, dirname, exists, isdir, isfile, islink, join
from shutil import rmtree
from stat import S_IEXEC, S_IWRITE, S_ISDIR, S_IMODE, S_ISREG, S_ISLNK
from time import sleep
from uuid import uuid4

from ..utils import on_win

log = getLogger(__name__)


def try_write(dir_path, heavy=False):
    """Test write access to a directory.

    Args:
        dir_path (str): directory to test write access
        heavy (bool): Actually create and delete a file, or do a faster os.access test.
           https://docs.python.org/dev/library/os.html?highlight=xattr#os.access

    Returns:
        bool

    """
    if not isdir(dir_path):
        return False
    if on_win or heavy:
        # try to create a file to see if `dir_path` is writable, see #2151
        temp_filename = join(dir_path, '.conda-try-write-%d' % getpid())
        try:
            with open(temp_filename, mode='wb') as fo:
                fo.write(b'This is a test file.\n')
            backoff_unlink(temp_filename)
            return True
        except (IOError, OSError):
            return False
        finally:
            backoff_unlink(temp_filename)
    else:
        return access(dir_path, W_OK)


def backoff_unlink(file_or_symlink_path):
    def _unlink(path):
        make_writable(path)
        unlink(path)

    try:
        exp_backoff_fn(lambda f: exists(f) and _unlink(f), file_or_symlink_path)
    except (IOError, OSError) as e:
        if e.errno not in (ENOENT,):
            # errno.ENOENT File not found error / No such file or directory
            raise


def backoff_rmdir(dirpath):
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
        recursive_make_writable(dirname(path))
        func(path)

    def rmdir(path):
        try:
            recursive_make_writable(path)
            exp_backoff_fn(rmtree, path, onerror=retry)
        except (IOError, OSError) as e:
            if e.errno == ENOENT:
                log.debug("no such file or directory: %s", path)
            else:
                raise

    for root, dirs, files in walk(dirpath, topdown=False):
        for file in files:
            backoff_unlink(join(root, file))
        for dir in dirs:
            rmdir(join(root, dir))

    rmdir(dirpath)


def make_writable(path):
    # try:
    #     mode = stat(path).st_mode
    # except (IOError, OSError) as e:
    #     if e.errno == ENOENT:
    #         return
    #     else:
    #         raise
    try:
        mode = stat(path).st_mode
        if S_ISDIR(mode):
            chmod(path, S_IMODE(mode) | S_IWRITE | S_IEXEC)
        elif S_ISREG(mode) or S_ISLNK(mode):
            chmod(path, S_IMODE(mode) | S_IWRITE)
        else:
            log.debug("path cannot be made writable: %s", path)
    except Exception as e:
        if getattr(e, 'errno', None) == ENOENT:
            raise
        else:
            log.error("Error making path writable: %s\n%r", path, e)
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


def exp_backoff_fn(fn, *args, **kwargs):
    """Mostly for retrying file operations that fail on Windows due to virus scanners"""
    if not on_win:
        return fn(*args, **kwargs)

    import random
    # with max_tries = 6, max total time ~= 3.2 sec
    # with max_tries = 7, max total time ~= 6.5 sec
    max_tries = 7
    for n in range(max_tries):
        try:
            result = fn(*args, **kwargs)
        except (OSError, IOError) as e:
            log.debug(repr(e))
            if e.errno in (EPERM, EACCES):
                if n == max_tries-1:
                    raise
                sleep_time = ((2 ** n) + random.random()) * 0.1
                caller_frame = sys._getframe(1)
                log.debug("retrying %s/%s %s() in %g sec",
                          basename(caller_frame.f_code.co_filename),
                          caller_frame.f_lineno, fn.__name__,
                          sleep_time)
                sleep(sleep_time)
            elif e.errno in (ENOENT,):
                # errno.ENOENT File not found error / No such file or directory
                raise
            else:
                log.error("Uncaught backoff with errno %d", e.errno)
                raise
        else:
            return result


def rm_rf(path, max_retries=5, trash=True):
    """
    Completely delete path
    max_retries is the number of times to retry on failure. The default is
    5. This only applies to deleting a directory.
    If removing path fails and trash is True, files will be moved to the trash directory.
    """
    if islink(path) or isfile(path):
        # Note that we have to check if the destination is a link because
        # exists('/path/to/dead-link') will return False, although
        # islink('/path/to/dead-link') is True.
        try:
            backoff_unlink(path)
            return
        except (OSError, IOError) as e:
            log.debug("%r errno %d\nCannot unlink %s.", e, e.errno, path)
            if trash and move_path_to_trash(path):
                return
            else:
                log.warn("Failed to remove %s.", path)

    elif isdir(path):
        try:
            # On Windows, always move to trash first.
            if trash and on_win and move_path_to_trash(path, preclean=False):
                return
            else:
                backoff_rmdir(path)
        finally:
            # If path was removed, ensure it's not in linked_data_
            if not isdir(path):
                from conda.install import delete_linked_data_any
                delete_linked_data_any(path)
    else:
        log.debug("rm_rf failed. Not a link, file, or directory: %s", path)


def delete_trash(prefix=None):
    from ..base.context import context
    for pkg_dir in context.pkgs_dirs:
        trash_dir = join(pkg_dir, '.trash')
        if not isdir(trash_dir):
            continue
        try:
            log.debug("Trying to delete the trash dir %s", trash_dir)
            backoff_rmdir(trash_dir)
        except (IOError, OSError) as e:
            log.info("Could not delete the trash dir %s\n%r", trash_dir, e)


def move_to_trash(prefix, f, tempdir=None):
    """
    Move a file or folder f from prefix to the trash

    tempdir is a deprecated parameter, and will be ignored.

    This function is deprecated in favor of `move_path_to_trash`.
    """
    return move_path_to_trash(join(prefix, f) if f else prefix)


def move_path_to_trash(path, preclean=True):
    """
    Move a path to the trash
    """
    # Try deleting the trash every time we use it.
    if preclean:
        delete_trash()

    from ..base.context import context
    for pkg_dir in context.pkgs_dirs:
        trash_dir = join(pkg_dir, '.trash')

        try:
            makedirs(trash_dir)
        except OSError as e1:
            if e1.errno != EEXIST:
                continue

        trash_file = join(trash_dir, text_type(uuid4()))

        try:
            rename(path, trash_file)
        except OSError as e:
            log.debug("Could not move %s to %s (%s)", path, trash_file, e)
        else:
            log.debug("Moved to trash: %s", path)
            from conda.install import delete_linked_data_any
            delete_linked_data_any(path)
            if not preclean:
                rm_rf(trash_file, max_retries=1, trash=False)
            return True

    return False
