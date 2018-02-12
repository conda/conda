# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from errno import EINVAL, EXDEV
from logging import getLogger
import os
from os import rename as os_rename, utime
from os.path import dirname, isdir
import re
from shutil import move

from . import exp_backoff_fn, mkdir_p, mkdir_p_sudo_safe
from .delete import rm_rf
from .link import lexists
from ...common.compat import on_win
from ...common.path import expand
from ...exceptions import NotWritableError

log = getLogger(__name__)

SHEBANG_REGEX = re.compile(br'^(#!((?:\\ |[^ \n\r])+)(.*))')


class CancelOperation(Exception):
    pass


def update_file_in_place_as_binary(file_full_path, callback):
    # callback should be a callable that takes one positional argument, which is the
    #   content of the file before updating
    # this method updates the file in-place, without releasing the file lock
    fh = None
    try:
        fh = exp_backoff_fn(open, file_full_path, 'rb+')
        log.trace("in-place update path locked for %s", file_full_path)
        data = fh.read()
        fh.seek(0)
        try:
            fh.write(callback(data))
            fh.truncate()
        except CancelOperation:
            pass  # NOQA
    finally:
        if fh:
            fh.close()


def rename(source_path, destination_path, force=False):
    if lexists(destination_path) and force:
        rm_rf(destination_path)
    if lexists(source_path):
        log.trace("renaming %s => %s", source_path, destination_path)
        try:
            os_rename(source_path, destination_path)
        except EnvironmentError as e:
            if e.errno in (EINVAL, EXDEV):
                # https://github.com/conda/conda/issues/6811
                # https://github.com/conda/conda/issues/6711
                log.trace("Could not rename %s => %s due to errno [%s]. Falling back"
                          " to copy/unlink", source_path, destination_path, e.errno)
                # https://github.com/moby/moby/issues/25409#issuecomment-238537855
                # shutil.move() falls back to copy+unlink
                move(source_path, destination_path)
            else:
                raise
    else:
        log.trace("cannot rename; source path does not exist '%s'", source_path)


def backoff_rename(source_path, destination_path, force=False):
    exp_backoff_fn(rename, source_path, destination_path, force)


def touch(path, mkdir=False, sudo_safe=False):
    # sudo_safe: use any time `path` is within the user's home directory
    # returns:
    #   True if the file did not exist but was created
    #   False if the file already existed
    # raises: permissions errors such as EPERM and EACCES
    try:
        path = expand(path)
        log.trace("touching path %s", path)
        if lexists(path):
            utime(path, None)
            return True
        else:
            dirpath = dirname(path)
            if not isdir(dirpath) and mkdir:
                if sudo_safe:
                    mkdir_p_sudo_safe(dirpath)
                else:
                    mkdir_p(dirpath)
            else:
                assert isdir(dirname(path))
            try:
                fh = open(path, 'a')
            except:
                raise
            else:
                fh.close()
                if sudo_safe and not on_win and os.environ.get('SUDO_UID') is not None:
                    uid = int(os.environ['SUDO_UID'])
                    gid = int(os.environ.get('SUDO_GID', -1))
                    log.trace("chowning %s:%s %s", uid, gid, path)
                    os.chown(path, uid, gid)
                return False
    except (IOError, OSError) as e:
        raise NotWritableError(path, e.errno, caused_by=e)
