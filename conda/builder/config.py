import sys
import os
from os.path import abspath, expanduser, join


ANA_PY = int(os.getenv('ANA_PY', 27))
ANA_NPY = int(os.getenv('ANA_NPY', 17))
PY3K = int(bool(ANA_PY >= 30))

if sys.platform == 'win32':
    croot = abspath(r'\_conda')
else:
    croot = expanduser('~/_conda')

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

    print 'ANA_PY:', ANA_PY
    print 'ANA_NPY:', ANA_NPY
    print 'subdir:', cc.subdir
