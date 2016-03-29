from __future__ import print_function, division, absolute_import

import re
import os
import sys
import subprocess
from os.path import isdir, isfile, join, expanduser

from conda.utils import memoized

def find_executable(executable, include_others=True):
    # backwards compatibility
    global dir_paths

    if include_others:
        if sys.platform == 'win32':
            dir_paths = [join(sys.prefix, 'Scripts'),
                         'C:\\cygwin\\bin']
        else:
            dir_paths = [join(sys.prefix, 'bin')]
    else:
        dir_paths = []

    dir_paths.extend(os.environ['PATH'].split(os.pathsep))

    for dir_path in dir_paths:
        if sys.platform == 'win32':
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
        if sys.platform == 'win32':
            dir_paths = [join(sys.prefix, 'Scripts'),
                         'C:\\cygwin\\bin']
        else:
            dir_paths = [join(sys.prefix, 'bin')]
    else:
        dir_paths = []

    if sys.platform == 'win32':
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


def filter_descr(cmd):
    args = [find_executable('conda-' + cmd), '--help']
    if not args[0]:
        print('failed: %s (could not find executable)' % (cmd))
        return
    try:
        output = subprocess.check_output(args)
    except (OSError, subprocess.CalledProcessError):
        print('failed: %s' % (' '.join(args)))
        return
    pat = re.compile(r'(\r?\n){2}(.*?)(\r?\n){2}', re.DOTALL)
    m = pat.search(output.decode('utf-8'))
    descr = ['<could not extract description>'] if m is None else m.group(2).splitlines()
    # XXX: using some stuff from textwrap would be better here, as it gets
    # longer than 80 characters
    print('    %-12s %s' % (cmd, descr[0]))
    for d in descr[1:]:
        print('                 %s' % d)


def help():
    print("\nother commands:")
    for cmd in find_commands():
        filter_descr(cmd)


if __name__ == '__main__':
    help()
