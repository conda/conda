from __future__ import print_function, division, absolute_import, unicode_literals

import os
import re
import sys
import sysconfig
from ..common.compat import on_win
from os.path import isdir, isfile, join, expanduser, basename

from ..utils import memoized, sys_prefix_unfollowed

def find_executable(executable, include_others=True):
    # backwards compatibility
    global dir_paths

    if include_others:
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

    dir_paths.extend(os.environ[str('PATH')].split(os.pathsep))

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

@memoized
def find_commands(include_others=True):

    if include_others:
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
    return sorted(res)
