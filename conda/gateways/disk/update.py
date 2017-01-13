# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from logging import getLogger
from os import rename, utime
from os.path import lexists
import re

from conda._vendor.auxlib.path import expand

from . import exp_backoff_fn

log = getLogger(__name__)

# in the rest of conda's code, os.rename is preferably imported from here
rename = rename

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


def backoff_rename(source_path, destination_path):
    if lexists(source_path):
        log.trace("renaming %s => %s", source_path, destination_path)
        exp_backoff_fn(rename, source_path, destination_path)
    else:
        log.trace("cannot rename; source path does not exist '%s'", source_path)
    return


def touch(path):
    # returns
    #   True if the file did not exist but was created
    #   False if the file already existed
    path = expand(path)
    log.trace("touching path %s", path)
    if lexists(path):
        utime(path, None)
        return True
    else:
        open(path, 'a').close()
        return False
