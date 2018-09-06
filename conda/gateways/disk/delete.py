# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import absolute_import, division, print_function, unicode_literals

from errno import ENOENT
from logging import getLogger
from os import listdir, removedirs, rename, rmdir, unlink
from os.path import abspath, isdir, join
import sys
from uuid import uuid4

from . import MAX_TRIES, exp_backoff_fn, mkdir_p
from .link import islink, lexists
from .permissions import make_writable
from ...base.context import context
from ...common.compat import PY3, ensure_fs_path_encoding, on_win, text_type
from ...common.io import Spinner, ThreadLimitedThreadPoolExecutor
from ...exceptions import NotWritableError
from ..._vendor.toolz import concatv


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
        # rm_rf_wait(path)
        future = self.executor.submit(rm_rf_wait, path)
        self.queue.append(future)

    def flush(self):
        # pass
        while self.queue:
            future = self.queue.pop(0)
            future.result()


rm_rf_queued = RM_RF_Queue()


def rm_rf_wait(path):
    """Block until path is deleted."""
    path = abspath(path)
    try:
        return _rmtree(path)
    finally:
        assert not lexists(path), "rm_rf failed for %s" % path


def try_rmdir_all_empty(dirpath, max_tries=MAX_TRIES):
    # This function uses removedirs to remove an empty directory and all parent empty directories.
    if not dirpath or not isdir(dirpath):
        return

    try:
        log.trace("Attempting to remove directory %s", dirpath)
        exp_backoff_fn(removedirs, dirpath, max_tries=max_tries)
    except EnvironmentError as e:
        # this function only guarantees trying, so we just swallow errors
        log.trace('%r', e)


def delete_trash():
    trash_dirs = tuple(td for td in (
        join(d, '.trash') for d in concatv(context.pkgs_dirs, (context.target_prefix,))
    ) if lexists(td))
    if not trash_dirs:
        return

    with Spinner("Removing trash", not context.verbosity and not context.quiet, context.json):
        _delete_trash_dirs(trash_dirs)


# def _rm_rf_no_move_to_trash(path):
#     path = abspath(path)
#
#     if isdir(path) and not islink(path):
#         log.trace("rm_rf_no_trash directory %s", path)
#         _rmdir_recursive(path)
#     elif lexists(path):
#         log.trace("rm_rf_no_trash path %s", path)
#         _backoff_unlink(path)
#     else:
#         log.trace("rm_rf_no_trash no-op. Not a link, file, or directory: %s", path)
#
#     assert not lexists(path), "rm_rf_no_trash failed for %s" % path
#     return True


def _backoff_unlink(file_or_symlink_path, max_tries=MAX_TRIES):
    exp_backoff_fn(_do_unlink, file_or_symlink_path, max_tries=max_tries)


def _make_win_path(path):
    path = abspath(path).rstrip('\\')
    return ensure_fs_path_encoding(path if path.startswith('\\\\?\\') else ('\\\\?\\' + path))


def _do_unlink(path):
    try:
        if on_win:
            path = _make_win_path(path)
            make_writable(path)
            handle_nonzero_success(SetFileAttributes(path, FILE_ATTRIBUTE_NORMAL))
            handle_nonzero_success(DeleteFile(path))
        if lexists(path):
            make_writable(path)
            unlink(path)
    except EnvironmentError as e:
        if e.errno == ENOENT:
            pass
        elif on_win:
            raise
        else:
            raise NotWritableError(path, e.errno, caused_by=e)


def _do_rmdir(path):
    try:
        if on_win:
            path = _make_win_path(path)
            make_writable(path)
            handle_nonzero_success(SetFileAttributes(path, FILE_ATTRIBUTE_NORMAL))
            handle_nonzero_success(RemoveDirectory(path))
        if lexists(path):
            make_writable(path)
            rmdir(path)
    except EnvironmentError as e:
        if e.errno == ENOENT:
            pass
        elif on_win:
            raise
        else:
            raise NotWritableError(path, e.errno, caused_by=e)


# def _backoff_rmdir_empty(dirpath, max_tries=MAX_TRIES):
#     exp_backoff_fn(_do_rmdir, dirpath, max_tries=max_tries)


def _rmtree_unix(path):
    path = abspath(path)
    try:
        if isdir(path) and not islink(path):
            dots = {'.', '..'}
            for file_name in listdir(path):
                if file_name in dots:
                    continue
                file_path = join(path, file_name)
                if isdir(file_path) and not islink(file_path):
                    _rmtree_unix(file_path)
                else:
                    _do_unlink(file_path)
            _do_rmdir(path)
        else:
            _do_unlink(path)
        return True
    except EnvironmentError as e:
        if e.errno == ENOENT:
            return False
        raise NotWritableError(path, e.errno, caused_by=e)


def _rmtree_win(path):
    win_path = _make_win_path(path)
    file_attr = GetFileAttributesW(win_path)

    dots = {'.', '..'}
    if file_attr & FILE_ATTRIBUTE_DIRECTORY:
        if file_attr & FILE_ATTRIBUTE_REPARSE_POINT:
            trash_path = _backoff_move_path_to_trash(path)
            _do_rmdir(trash_path)
        else:
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
                    if file_attr & FILE_ATTRIBUTE_REPARSE_POINT:
                        log.trace("remove reparse point %s", file_path)
                        trash_path = _backoff_move_path_to_trash(file_path)
                        _do_rmdir(trash_path)
                    else:
                        _rmtree_win(file_path)
                else:
                    trash_path = _backoff_move_path_to_trash(file_path)
                    _do_unlink(trash_path)
            trash_path = _backoff_move_path_to_trash(path)
            _do_rmdir(trash_path)
    else:
        trash_path = _backoff_move_path_to_trash(path)
        _do_unlink(trash_path)


if on_win:
    _rmtree = _rmtree_win
else:
    _rmtree = _rmtree_unix

# def _rmdir_recursive(path, max_tries=MAX_TRIES):
#     if on_win:
#         win_path = _make_win_path(path)
#         file_attr = GetFileAttributesW(win_path)
#
#         dots = {'.', '..'}
#         if file_attr & FILE_ATTRIBUTE_DIRECTORY:
#             if file_attr & FILE_ATTRIBUTE_REPARSE_POINT:
#                 _backoff_rmdir_empty(win_path, max_tries=max_tries)
#             else:
#                 for ffrec in FindFiles(ensure_fs_path_encoding(win_path + '\\*.*')):
#                     file_name = ensure_fs_path_encoding(ffrec[8])
#                     if file_name in dots:
#                         continue
#                     file_attr = ffrec[0]
#                     # reparse_tag = ffrec[6]
#                     file_path = join(path, file_name)
#                     # log.debug("attributes for [%s] [%s] are %s" %
#                     #           (file_path, reparse_tag, hex(file_attr)))
#                     if file_attr & FILE_ATTRIBUTE_DIRECTORY:
#                         if file_attr & FILE_ATTRIBUTE_REPARSE_POINT:
#                             _backoff_rmdir_empty(win_path, max_tries=max_tries)
#                         else:
#                             _rmdir_recursive(file_path, max_tries=max_tries)
#                     else:
#                         _backoff_unlink(file_path, max_tries=max_tries)
#                 _backoff_rmdir_empty(win_path, max_tries=max_tries)
#         else:
#             _backoff_unlink(path, max_tries=max_tries)
#     else:
#         path = abspath(path)
#         if not lexists(path):
#             return
#         elif isdir(path) and not islink(path):
#             dots = {'.', '..'}
#             for file_name in listdir(path):
#                 if file_name in dots:
#                     continue
#                 file_path = join(path, file_name)
#                 if isdir(file_path) and not islink(file_path):
#                     _rmdir_recursive(file_path, max_tries=max_tries)
#                 else:
#                     _backoff_unlink(file_path, max_tries=max_tries)
#             _backoff_rmdir_empty(path, max_tries=max_tries)
#         else:
#             _backoff_unlink(path, max_tries=max_tries)


def _rmtree_win_no_move_to_trash(path):
    win_path = _make_win_path(path)
    file_attr = GetFileAttributesW(win_path)

    dots = {'.', '..'}
    if file_attr & FILE_ATTRIBUTE_DIRECTORY:
        if file_attr & FILE_ATTRIBUTE_REPARSE_POINT:
            _do_rmdir(path)
        else:
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
                    if file_attr & FILE_ATTRIBUTE_REPARSE_POINT:
                        log.trace("remove reparse point %s", file_path)
                        _do_rmdir(file_path)
                    else:
                        _rmtree_win(file_path)
                else:
                    _do_unlink(file_path)
            _do_rmdir(path)
    else:
        trash_path = _backoff_move_path_to_trash(path)
        _do_unlink(trash_path)


def _delete_trash_dirs(trash_dirs, ignore_errors=True):
    rm_rf_queued.flush()
    for trash_dir in trash_dirs:
        if not lexists(trash_dir):
            continue
        log.trace("removing trash for %s", trash_dir)
        try:
            if on_win:
                _rmtree_win_no_move_to_trash(trash_dir)
            else:
                _rmtree_unix(trash_dir)
        except EnvironmentError as e:
            log.info("Unable to delete trash path: %s\n  %r", trash_dir, e)
            if ignore_errors:
                return
            raise NotWritableError(trash_dir, e.errno, caused_by=e)


def _move_path_to_trash(path):
    trash_dir = context.trash_dir
    trash_file = join(trash_dir, text_type(uuid4()))
    try:
        mkdir_p(trash_dir)
    except EnvironmentError as e:
        raise NotWritableError(path, e.errno, caused_by=e)
    try:
        if on_win:
            trash_file = _make_win_path(trash_file)
            path = _make_win_path(path)
            make_writable(path)
            handle_nonzero_success(SetFileAttributes(path, FILE_ATTRIBUTE_NORMAL))
        # This rename assumes the trash_file is on the same file system as the file being trashed.
        rename(path, trash_file)
        return trash_file
    except EnvironmentError as e:
        if e.errno == ENOENT:
            return trash_file
        log.debug("EnvironmentError in _move_path_to_trash:\n"
                  "  path: %s\n"
                  "  trash_file: %s\n"
                  "  error: %r",
                  path, trash_file, e)
        raise


def _backoff_move_path_to_trash(file_or_symlink_path, max_tries=MAX_TRIES):
    return exp_backoff_fn(_move_path_to_trash, file_or_symlink_path, max_tries=max_tries)


if on_win:
    import ctypes
    from win32api import FindFiles
    from win32file import FILE_ATTRIBUTE_DIRECTORY, GetFileAttributesW

    if PY3:
        import builtins
    else:
        import __builtin__ as builtins

    SetFileAttributes = ctypes.windll.kernel32.SetFileAttributesW
    SetFileAttributes.argtypes = ctypes.wintypes.LPWSTR, ctypes.wintypes.DWORD
    SetFileAttributes.restype = ctypes.wintypes.BOOL

    DeleteFile = ctypes.windll.kernel32.DeleteFileW
    DeleteFile.argtypes = ctypes.wintypes.LPWSTR,
    DeleteFile.restype = ctypes.wintypes.BOOL

    RemoveDirectory = ctypes.windll.kernel32.RemoveDirectoryW
    RemoveDirectory.argtypes = ctypes.wintypes.LPWSTR,
    RemoveDirectory.restype = ctypes.wintypes.BOOL

    FILE_ATTRIBUTE_NORMAL = 0x80
    FILE_ATTRIBUTE_REPARSE_POINT = 0x400

    class WindowsError(builtins.WindowsError):
        """
        More info about errors at
        http://msdn.microsoft.com/en-us/library/ms681381(VS.85).aspx
        """

        def __init__(self, value=None):
            if value is None:
                value = ctypes.windll.kernel32.GetLastError()
            strerror = format_system_message(value)
            if sys.version_info > (3, 3):
                args = 0, strerror, None, value
            else:
                args = value, strerror
            super(WindowsError, self).__init__(*args)

        @property
        def message(self):
            return self.strerror

        @property
        def code(self):
            return self.winerror

        def __str__(self):
            return "[%s] %s" % (self.errno, self.message)

        def __repr__(self):
            e = WindowsError()
            log.error('%r', e)
            raise e

    def format_system_message(errno):
        """
        Call FormatMessage with a system error number to retrieve
        the descriptive error message.
        """
        # first some flags used by FormatMessageW
        ALLOCATE_BUFFER = 0x100
        FROM_SYSTEM = 0x1000

        # Let FormatMessageW allocate the buffer (we'll free it below)
        # Also, let it know we want a system error message.
        flags = ALLOCATE_BUFFER | FROM_SYSTEM
        source = None
        message_id = errno
        language_id = 0
        result_buffer = ctypes.wintypes.LPWSTR()
        buffer_size = 0
        arguments = None
        bytes = ctypes.windll.kernel32.FormatMessageW(
            flags,
            source,
            message_id,
            language_id,
            ctypes.byref(result_buffer),
            buffer_size,
            arguments,
        )
        # note the following will cause an infinite loop if GetLastError
        #  repeatedly returns an error that cannot be formatted, although
        #  this should not happen.
        handle_nonzero_success(bytes)
        message = result_buffer.value
        ctypes.windll.kernel32.LocalFree(result_buffer)
        return message

    def handle_nonzero_success(result):
        if result == 0:
            raise WindowsError()
