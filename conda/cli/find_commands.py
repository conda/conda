# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import absolute_import, division, print_function, unicode_literals

from functools import lru_cache
import os
from os.path import basename, expanduser, isdir, isfile, join
import re
import sys
import sysconfig

from ..common.compat import on_win


def find_executable(executable, include_others=True):
    # backwards compatibility
    global dir_paths

    if include_others:
        from ..utils import sys_prefix_unfollowed
        prefixes = [sys_prefix_unfollowed()]
        if sys.prefix != prefixes[0]:
            prefixes.append(sys.prefix)
        dir_paths = [join(p, basename(sysconfig.get_path('scripts')))
                     for p in prefixes]
        # Is this still needed?
        if on_win:
            dir_paths.append('C:\\cygwin\\bin')
    else:
        dir_paths = []

    dir_paths.extend(os.environ.get('PATH', '').split(os.pathsep))

    for dir_path in dir_paths:
        if on_win:
            for ext in ('.exe', '.bat', ''):
                path = join(dir_path, executable + ext)
                if isfile(path):
                    return path
        else:
            path = join(dir_path, executable)
            if isfile(expanduser(path)):
                return expanduser(path)
    return None


@lru_cache(maxsize=None)
def find_commands(include_others=True):

    if include_others:
        from ..utils import sys_prefix_unfollowed
        prefixes = [sys_prefix_unfollowed()]
        if sys.prefix != prefixes[0]:
            prefixes.append(sys.prefix)
        dir_paths = [join(p, basename(sysconfig.get_path('scripts')))
                     for p in prefixes]
        # Is this still needed?
        if on_win:
            dir_paths.append('C:\\cygwin\\bin')
    else:
        dir_paths = []

    if on_win:
        pat = re.compile(r'conda-([\w\-]+)\.(exe|bat)$')
    else:
        pat = re.compile(r'conda-([\w\-]+)$')

    res = set()
    for dir_path in dir_paths:
        if not isdir(dir_path):
            continue
        for fn in os.listdir(dir_path):
            if not isfile(join(dir_path, fn)):
                continue
            m = pat.match(fn)
            if m:
                res.add(m.group(1))
    return tuple(sorted(res))
