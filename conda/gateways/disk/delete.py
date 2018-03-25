# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from errno import ENOENT
from logging import getLogger
from os import listdir, removedirs, rename, rmdir, unlink
from os.path import abspath, isdir, join
from uuid import uuid4

from . import MAX_TRIES, exp_backoff_fn, mkdir_p
from .link import islink, lexists
from .permissions import make_writable
from ...base.context import context
from ...common.compat import ensure_fs_path_encoding, on_win, text_type
from ...common.io import Spinner, ThreadLimitedThreadPoolExecutor

try:
    from cytoolz.itertoolz import concatv
except ImportError:  # pragma: no cover
    from ..._vendor.toolz.itertoolz import concatv  # NOQA

if on_win:
    from ctypes import FormatError
    from pywintypes import error as PyWinTypeError
    from win32api import FindFiles
    from win32file import (DeleteFileW, FILE_ATTRIBUTE_DIRECTORY, FILE_ATTRIBUTE_NORMAL,
                           GetFileAttributesW, RemoveDirectory, SetFileAttributesW)


log = getLogger(__name__)


class RM_RF_Queue(object):
    """
    Remove paths asynchronously.  Must always call `.flush()` to ensure paths
    are actually removed.
    """

    def __init__(self):
        self.executor = ThreadLimitedThreadPoolExecutor()
        self.queue = []

    def __call__(self, path):
        self.submit(path)

    def submit(self, path):
        future = self.executor.submit(rm_rf_wait, path)
        self.queue.append(future)

    def flush(self):
        while self.queue:
            future = self.queue.pop(0)
            future.result()


rm_rf_queued = RM_RF_Queue()


def rm_rf_wait(path):
    """Block until path is deleted."""
    path = abspath(path)
    try:
        if isdir(path) and not islink(path):
            log.trace("rm_rf directory %s", path)
            try:
                _rmdir_recursive(path)
            except EnvironmentError:
                if on_win:
                    _move_path_to_trash(path)
                else:
                    raise
        elif lexists(path):
            log.trace("rm_rf path %s", path)
            try:
                _backoff_unlink(path)
            except EnvironmentError:
                if on_win:
                    _move_path_to_trash(path)
                else:
                    raise
        else:
            log.trace("rm_rf no-op. Not a link, file, or directory: %s", path)
        return True
    finally:
        assert not lexists(path), "rm_rf failed for %s" % path


def _rm_rf_no_move_to_trash(path):
    path = abspath(path)
    try:
        if isdir(path) and not islink(path):
            log.trace("rm_rf_no_trash directory %s", path)
            _rmdir_recursive(path)
        elif lexists(path):
            log.trace("rm_rf_no_trash path %s", path)
            _backoff_unlink(path)
        else:
            log.trace("rm_rf_no_trash no-op. Not a link, file, or directory: %s", path)
        return True
    finally:
        assert not lexists(path), "rm_rf_no_trash failed for %s" % path


def _backoff_unlink(file_or_symlink_path, max_tries=MAX_TRIES):
    exp_backoff_fn(_do_unlink, file_or_symlink_path, max_tries=max_tries)


def _make_win_path(path):
    path = abspath(path).rstrip('\\')
    return ensure_fs_path_encoding(path if path.startswith('\\\\?\\') else '\\\\?\\%s' % path)


def _win_fs_syscall(func, *args):
    try:
        if 0 == func(*args):
            error = OSError(FormatError())
            if error.errno != ENOENT:
                raise error
    except PyWinTypeError:
        error = OSError(FormatError())
        if error.errno != ENOENT:
            raise error


def _do_unlink(path):
    if on_win:
        win_path = _make_win_path(path)
        _win_fs_syscall(SetFileAttributesW, win_path, FILE_ATTRIBUTE_NORMAL)
        _win_fs_syscall(DeleteFileW, win_path)
        if lexists(win_path):
            try:
                make_writable(win_path)
                unlink(win_path)
            except EnvironmentError as e:
                if e.errno == ENOENT:
                    pass
                else:
                    raise
    else:
        try:
            make_writable(path)
            unlink(path)
        except EnvironmentError as e:
            if e.errno == ENOENT:
                pass
            else:
                raise


def _do_rmdir(path):
    if on_win:
        win_path = _make_win_path(path)
        _win_fs_syscall(SetFileAttributesW, win_path, FILE_ATTRIBUTE_NORMAL)
        _win_fs_syscall(RemoveDirectory, win_path)
    else:
        try:
            make_writable(path)
            rmdir(path)
        except EnvironmentError as e:
            if e.errno == ENOENT:
                pass
            else:
                raise


def _backoff_rmdir_empty(dirpath, max_tries=MAX_TRIES):
    exp_backoff_fn(_do_rmdir, dirpath, max_tries=max_tries)


def _rmdir_recursive(path, max_tries=MAX_TRIES):
    if on_win:
        win_path = _make_win_path(path)
        file_attr = GetFileAttributesW(win_path)

        dots = {'.', '..'}
        if file_attr & FILE_ATTRIBUTE_DIRECTORY:
            for ffrec in FindFiles(ensure_fs_path_encoding(win_path + '\\*.*')):
                file_name = ensure_fs_path_encoding(ffrec[8])
                if file_name in dots:
                    continue
                file_attr = ffrec[0]
                # reparse_tag = ffrec[6]
                file_path = join(path, file_name)
                # log.debug("attributes for [%s] [%s] are %s" %
                #           (file_path, reparse_tag, hex(file_attr)))
                if file_attr & FILE_ATTRIBUTE_DIRECTORY:
                    _rmdir_recursive(file_path, max_tries=max_tries)
                else:
                    _backoff_unlink(file_path, max_tries=max_tries)
            _backoff_rmdir_empty(win_path, max_tries=max_tries)
        else:
            _backoff_unlink(path, max_tries=max_tries)
    else:
        path = abspath(path)
        if not lexists(path):
            return
        elif isdir(path) and not islink(path):
            dots = {'.', '..'}
            for file_name in listdir(path):
                if file_name in dots:
                    continue
                file_path = join(path, file_name)
                if isdir(file_path) and not islink(file_path):
                    _rmdir_recursive(file_path, max_tries=max_tries)
                else:
                    _backoff_unlink(file_path, max_tries=max_tries)
            _backoff_rmdir_empty(path, max_tries=max_tries)
        else:
            _backoff_unlink(path, max_tries=max_tries)


def delete_trash():
    trash_dirs = tuple(td for td in (
        join(d, '.trash') for d in concatv(context.pkgs_dirs, (context.target_prefix,))
    ) if lexists(td))
    if not trash_dirs:
        return

    with Spinner("Removing trash", not context.verbosity and not context.quiet, context.json):
        _delete_trash_dirs(trash_dirs)


def _delete_trash_dirs(trash_dirs):
    for trash_dir in trash_dirs:
        log.trace("removing trash for %s", trash_dir)
        try:
            _rm_rf_no_move_to_trash(trash_dir)
        except EnvironmentError as e:
            log.info("Unable to delete trash path: %s\n  %r", trash_dir, e)
    rm_rf_queued.flush()


def _move_path_to_trash(path):
    trash_dir = context.trash_dir
    mkdir_p(trash_dir)
    trash_file = join(trash_dir, text_type(uuid4()))
    if on_win:
        trash_file = _make_win_path(trash_file)
        path = _make_win_path(path)
    # This rename assumes the trash_file is on the same file system as the file being trashed.
    rename(path, trash_file)
    return trash_file


def try_rmdir_all_empty(dirpath, max_tries=MAX_TRIES):
    if not dirpath or not isdir(dirpath):
        return

    try:
        log.trace("Attempting to remove directory %s", dirpath)
        exp_backoff_fn(removedirs, dirpath, max_tries=max_tries)
    except (IOError, OSError) as e:
        # this function only guarantees trying, so we just swallow errors
        log.trace('%r', e)
