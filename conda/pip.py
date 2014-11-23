"""
Functions related to core conda functionality that relates to pip
"""
from __future__ import absolute_import, print_function
from os.path import isfile, join
import re
import subprocess
import sys


def pip_args(prefix):
    """
    return the arguments required to invoke pip (in prefix), or None if pip
    is not installed
    """
    if sys.platform == 'win32':
        pip_path = join(prefix, 'Scripts', 'pip-script.py')
        py_path = join(prefix, 'python.exe')
    else:
        pip_path = join(prefix, 'bin', 'pip')
        py_path = join(prefix, 'bin', 'python')
    if isfile(pip_path) and isfile(py_path):
        return [py_path, pip_path]
    else:
        return None


# TODO: Refactor internals into a function that returns a list of pip
#       installed packages instead of modifying installed
def add_pip_installed(prefix, installed, json=None, output=True):
    # Here for backwards compatibility
    if type(json) is bool:
        output = not json

    args = pip_args(prefix)
    if args is None:
        return
    args.append('list')
    try:
        pipinst = subprocess.check_output(
            args, universal_newlines=True
        ).split('\n')
    except Exception:
        # Any error should just be ignored
        if output:
            print("# Warning: subprocess call to pip failed")
        return

    # For every package in pipinst that is not already represented
    # in installed append a fake name to installed with 'pip'
    # as the build string
    conda_names = {d.rsplit('-', 2)[0] for d in installed}
    pat = re.compile('([\w.-]+)\s+\((.+)\)')
    for line in pipinst:
        line = line.strip()
        if not line:
            continue
        m = pat.match(line)
        if m is None:
            if output:
                print('Could not extract name and version from: %r' % line)
            continue
        name, version = m.groups()
        name = name.lower()
        if ', ' in version:
            # Packages installed with setup.py develop will include a path in
            # the version. They should be included here, even if they are
            # installed with conda, as they are preferred over the conda
            # version. We still include the conda version, though, because it
            # is still installed.

            version, path = version.split(', ')
            # We do this because the code below uses rsplit('-', 2)
            version = version.replace('-', ' ')
            installed.add('%s (%s)-%s-<pip>' % (name, path, version))
        elif name not in conda_names:
            installed.add('%s-%s-<pip>' % (name, version))
