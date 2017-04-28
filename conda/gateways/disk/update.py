# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import json
from logging import getLogger
from os import rename as os_rename, utime
from os.path import dirname, isdir, join
import re

from . import exp_backoff_fn, mkdir_p
from .link import lexists
from .delete import rm_rf
from ... import CondaError
from ..._vendor.auxlib.entity import EntityEncoder
from ..._vendor.auxlib.ish import dals
from ..._vendor.auxlib.path import expand
from ...common.compat import ensure_binary, ensure_text_type
from ...common.path import win_path_backout, win_path_ok

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
        os_rename(source_path, destination_path)
    else:
        log.trace("cannot rename; source path does not exist '%s'", source_path)


def backoff_rename(source_path, destination_path, force=False):
    exp_backoff_fn(rename, source_path, destination_path, force)


def touch(path, mkdir=False):
    # returns
    #   True if the file did not exist but was created
    #   False if the file already existed
    # raises permissions errors such as EPERM and EACCES
    path = expand(path)
    log.trace("touching path %s", path)
    if lexists(path):
        utime(path, None)
        return True
    else:
        dirpath = dirname(path)
        if not isdir(dirpath) and mkdir:
            mkdir_p(dirpath)
        else:
            assert isdir(dirname(path))
        try:
            fh = open(path, 'a')
        except:
            raise
        else:
            fh.close()
            return False


def add_leased_path(source_prefix, source_short_path, target_prefix, target_path):
    leased_path_entry = {
        "_path": source_short_path,
        "target_path": win_path_backout(target_path),
        "target_prefix": win_path_ok(target_prefix),
    }

    def _add_leased_path(binary_data):
        prefix_metadata = json.loads(ensure_text_type(binary_data).strip()) or {}
        leased_paths = prefix_metadata.setdefault('leased_paths', [])
        current_lp = next((lp for lp in leased_paths if lp['_path'] == source_short_path), None)
        if current_lp:
            message = dals("""
            A path in prefix '%(source_prefix)s'
            is already leased by another environment.
              path: %(source_short_path)s
              target prefix: %(target_prefix)s
              target path: %(target_path)s
            """)
            raise CondaError(message, source_prefix=source_prefix,
                             source_short_path=source_short_path, target_prefix=target_prefix,
                             target_path=target_path)
        leased_paths.append(leased_path_entry)
        return ensure_binary(json.dumps(prefix_metadata, indent=2, sort_keys=True,
                                        separators=(',', ': '), cls=EntityEncoder))

    prefix_metadata_path = join(source_prefix, 'conda-meta', 'prefix_metadata.json')
    update_file_in_place_as_binary(prefix_metadata_path, _add_leased_path)
