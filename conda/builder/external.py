from __future__ import print_function, division, absolute_import

import os
import sys
from os.path import isfile, join

import conda.config as cc
from conda.builder.config import build_prefix



if sys.platform == 'win32':
    dir_paths = [join(build_prefix, 'Scripts'),
                 join(cc.root_dir, 'Scripts'),
                 'C:\cygwin\bin']
else:
    dir_paths = [join(build_prefix, 'bin'),
                 join(cc.root_dir, 'bin'),]

dir_paths.extend(os.environ['PATH'].split(os.pathsep))

def find_executable(executable):
    for dir_path in dir_paths:
        if sys.platform == 'win32':
            for ext in  '.exe', '.bat', '':
                path = join(dir_path, executable + ext)
                if isfile(path):
                    return path
        else:
            path = join(dir_path, executable)
            if isfile(path):
                return path
    return None
