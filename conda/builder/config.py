import sys
import os
from os.path import abspath, expanduser


if sys.platform == 'win32':
    build_root = abspath(r'\_conda_build')
else:
    build_root = expanduser('~/_conda_build')


ANA_PY = int(os.getenv('ANA_PY', 27))
ANA_NPY = int(os.getenv('ANA_NPY', 17))
