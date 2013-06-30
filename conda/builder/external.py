import os
import sys
from os.path import isfile, join

import conda.config as cc
from config import build_prefix



if sys.platform == 'win32':
    dir_paths = [join(build_prefix, 'Scripts'),
                 join(cc.root_dir, 'Scripts'),
                 'C:\cygwin\bin']
    dir_paths.extend(os.environ['PATH'].split(os.pathsep))
else:
    dir_paths = [join(build_prefix, 'bin'),
                 join(cc.root_dir, 'bin'),
                 '/usr/local/bin', '/bin', '/usr/bin']


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
