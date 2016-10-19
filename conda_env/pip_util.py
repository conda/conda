"""
Functions related to core conda functionality that relates to pip

NOTE: This modules used to in conda, as conda/pip.py
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
        ret = [py_path, pip_path]

        # Check the version of pip
        # --disable-pip-version-check was introduced in pip 6.0
        # If older than that, they should probably get the warning anyway.
        pip_version = subprocess.check_output(ret + ['-V']).decode('utf-8').split()[1]
        major_ver = pip_version.split('.')[0]
        if int(major_ver) >= 6:
            ret.append('--disable-pip-version-check')
        return ret
    else:
        return None


class PipPackage(dict):
    def __str__(self):
        if 'path' in self:
            return '%s (%s)-%s-<pip>' % (
                self['name'],
                self['path'],
                self['version']
            )
        return '%s-%s-<pip>' % (self['name'], self['version'])


def installed(prefix, output=True):
    args = pip_args(prefix)
    if args is None:
        return
    args.append('list')
    try:
        pipinst = subprocess.check_output(
            args, universal_newlines=True
        ).splitlines()
    except Exception:
        # Any error should just be ignored
        if output:
            print("# Warning: subprocess call to pip failed")
        return

    # For every package in pipinst that is not already represented
    # in installed append a fake name to installed with 'pip'
    # as the build string
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
        kwargs = {
            'name': name,
            'version': version,
        }
        if ', ' in version:
            # Packages installed with setup.py develop will include a path in
            # the version. They should be included here, even if they are
            # installed with conda, as they are preferred over the conda
            # version. We still include the conda version, though, because it
            # is still installed.

            version, path = version.split(', ')
            # We do this because the code below uses rsplit('-', 2)
            version = version.replace('-', ' ')
            kwargs.update({
                'path': path,
                'version': version,
            })
        yield PipPackage(**kwargs)


def add_pip_installed(prefix, installed_pkgs, json=None, output=True):
    # Defer to json for backwards compatibility
    if isinstance(json, bool):
        output = not json

    # TODO Refactor so installed is a real list of objects/dicts
    #      instead of strings allowing for direct comparison
    # split :: to get rid of channel info
    conda_names = {d.quad[0] for d in installed_pkgs}
    for pip_pkg in installed(prefix, output=output):
        if pip_pkg['name'] in conda_names and 'path' not in pip_pkg:
            continue
        installed_pkgs.add(str(pip_pkg))
