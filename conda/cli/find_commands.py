from __future__ import print_function, division, absolute_import

import re
import os
import sys
from subprocess import check_output
from os.path import isdir, isfile, join



if sys.platform == 'win32':
    dir_paths = [join(sys.prefix, 'Scripts')]
else:
    dir_paths = [join(sys.prefix, 'bin')]

dir_paths.extend(os.environ['PATH'].split(os.pathsep))


def find_executable(cmd):
    executable = 'conda-%s' % cmd
    for dir_path in dir_paths:
        if sys.platform == 'win32':
            for ext in  '.exe', '.bat':
                path = join(dir_path, executable + ext)
                if isfile(path):
                    return path
        else:
            path = join(dir_path, executable)
            if isfile(path):
                return path
    return None


def find_commands():
    if sys.platform == 'win32':
        pat = re.compile(r'conda-(\w+)\.(exe|bat)$')
    else:
        pat = re.compile(r'conda-(\w+)$')

    res = set()
    for dir_path in dir_paths:
        if not isdir(dir_path):
            continue
        for fn in os.listdir(dir_path):
            m = pat.match(fn)
            if m:
                res.add(m.group(1))
    return sorted(res)


def filter_descr(cmd):
    output = check_output([find_executable(cmd), '--help'])
    descr = output.split('\n\n')[1]
    print('%-20s %s' % (cmd, descr))


def help():
    for cmd in find_commands():
        filter_descr(cmd)


if __name__ == '__main__':
    help()
