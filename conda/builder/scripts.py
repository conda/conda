from __future__ import print_function, division, absolute_import

import re
import os
import sys
from os.path import isdir, join

from conda.builder.config import build_prefix, build_python


BAT_PROXY = """\
@echo off
set PYFILE=%~f0
set PYFILE=%PYFILE:~0,-4%-script.py
"%~f0\\..\\..\\python.exe" "%PYFILE%" %*
"""

PY_TMPL = """\
if __name__ == '__main__':
    import sys
    from %s import %s

    sys.exit(%s())
"""

bin_dirname = 'Scripts' if sys.platform == 'win32' else 'bin'

entry_pat = re.compile('\s*([\w\-\.]+)\s*=\s*([\w.]+):(\w+)\s*$')


def iter_entry_points(items):
    for item in items:
        m = entry_pat.match(item)
        if m is None:
            sys.exit("Error cound not match entry point: %r" % item)
        yield m.groups()


def create_entry_point(path, module, func):
    pyscript = PY_TMPL % (module, func, func)
    if sys.platform == 'win32':
        with open(path + '-script.py', 'w') as fo:
            fo.write(pyscript)
        with open(path + '.bat', 'w') as fo:
            fo.write(BAT_PROXY)
    else:
        with open(path, 'w') as fo:
            fo.write('#!%s\n' % build_python)
            fo.write(pyscript)
        os.chmod(path, int('755', 8))


def create_entry_points(items):
    if not items:
        return
    bin_dir = join(build_prefix, bin_dirname)
    if not isdir(bin_dir):
        os.mkdir(bin_dir)
    for cmd, module, func in iter_entry_points(items):
        create_entry_point(join(bin_dir, cmd), module, func)
