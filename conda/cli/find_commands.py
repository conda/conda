from __future__ import print_function, division, absolute_import

import os
import re
import sys
from os.path import isdir, isfile, join, expanduser

from ..utils import memoized, on_win


def find_executable(executable, include_others=True):
    # backwards compatibility
    global dir_paths

    if include_others:
        if on_win:
            dir_paths = [join(sys.prefix, 'Scripts'),
                         'C:\\cygwin\\bin']
        else:
            dir_paths = [join(sys.prefix, 'bin')]
    else:
        dir_paths = []

    dir_paths.extend(os.environ['PATH'].split(os.pathsep))

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
        if on_win:
            dir_paths = [join(sys.prefix, 'Scripts'),
                         'C:\\cygwin\\bin']
        else:
            dir_paths = [join(sys.prefix, 'bin')]
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
