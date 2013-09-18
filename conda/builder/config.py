from __future__ import print_function, division, absolute_import

import os
import sys
from os.path import abspath, expanduser, join

import conda.config as cc


CONDA_PY = int(os.getenv('CONDA_PY', cc.default_python.replace('.', '')))
CONDA_NPY = int(os.getenv('CONDA_NPY', 17))
PY3K = int(bool(CONDA_PY >= 30))

if cc.root_writable:
    croot = join(cc.root_dir, 'conda-bld')
else:
    croot = abspath(expanduser('~/conda-bld'))

build_prefix = join(cc.envs_dirs[0], '_build')
test_prefix = join(cc.envs_dirs[0], '_test')

def _get_python(prefix):
    if sys.platform == 'win32':
        res = join(prefix, 'python.exe')
    else:
        res = join(prefix, 'bin/python')
        if PY3K:
            res += '3'
    return res

build_python = _get_python(build_prefix)
test_python = _get_python(test_prefix)


def show():
    import conda.config as cc

    print('CONDA_PY:', CONDA_PY)
    print('CONDA_NPY:', CONDA_NPY)
    print('subdir:', cc.subdir)
    print('croot:', croot)
