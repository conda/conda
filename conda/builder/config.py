from __future__ import print_function, division, absolute_import

import sys
import os
from os.path import join

import conda.config as cc


CONDA_PY = int(os.getenv('CONDA_PY', 27))
CONDA_NPY = int(os.getenv('CONDA_NPY', 17))
PY3K = int(bool(CONDA_PY >= 30))

croot = join(cc.root_dir, 'conda-bld')
build_prefix = join(croot, 'build_env')
test_prefix = join(croot, 'test_env')

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

    print 'CONDA_PY:', CONDA_PY
    print 'CONDA_NPY:', CONDA_NPY
    print 'subdir:', cc.subdir
