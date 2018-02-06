"""
Functions related to core conda functionality that relates to pip

NOTE: This modules used to in conda, as conda/pip.py
"""
from __future__ import absolute_import, print_function

import json
import os
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
        return ret, pip_version
    else:
        return None, None


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
    args, pip_version = pip_args(prefix)
    if args is None:
        return

    pip_major_version = int(pip_version.split('.', 1)[0])

    env = os.environ.copy()
    env[str('PIP_FORMAT')] = str('legacy')
    args.append('list')

    if pip_major_version >= 9:
        args += ['--format', 'json']

    try:
        pip_stdout = subprocess.check_output(args, universal_newlines=True, env=env)
    except Exception:
        # Any error should just be ignored
        if output:
            print("# Warning: subprocess call to pip failed")
        return

    if pip_major_version >= 9:
        pkgs = json.loads(pip_stdout)

        # For every package in pipinst that is not already represented
        # in installed append a fake name to installed with 'pip'
        # as the build string
        for kwargs in pkgs:
            kwargs['name'] = kwargs['name'].lower()
            if ', ' in kwargs['version']:
                # Packages installed with setup.py develop will include a path in
                # the version. They should be included here, even if they are
                # installed with conda, as they are preferred over the conda
                # version. We still include the conda version, though, because it
                # is still installed.

                version, path = kwargs['version'].split(', ', 1)
                # We do this because the code below uses rsplit('-', 2)
                version = version.replace('-', ' ')
                kwargs['version'] = version
                kwargs['path'] = path
            yield PipPackage(**kwargs)
    else:
        # For every package in pipinst that is not already represented
        # in installed append a fake name to installed with 'pip'
        # as the build string
        pat = re.compile('([\w.-]+)\s+\((.+)\)')
        for line in pip_stdout.splitlines():
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


# canonicalize_{regex,name} inherited from packaging/utils.py
# Used under BSD license
_canonicalize_regex = re.compile(r"[-_.]+")


def _canonicalize_name(name):
    # This is taken from PEP 503.
    return _canonicalize_regex.sub("-", name).lower()


def add_pip_installed(prefix, installed_pkgs, json=None, output=True):
    # Defer to json for backwards compatibility
    if isinstance(json, bool):
        output = not json

    # TODO Refactor so installed is a real list of objects/dicts
    #      instead of strings allowing for direct comparison
    # split :: to get rid of channel info

    # canonicalize names for pip comparison
    # because pip normalizes `foo_bar` to `foo-bar`
    conda_names = {_canonicalize_name(d.quad[0]) for d in installed_pkgs}
    for pip_pkg in installed(prefix, output=output):
        pip_name = _canonicalize_name(pip_pkg['name'])
        if pip_name in conda_names and 'path' not in pip_pkg:
            continue
        installed_pkgs.add(str(pip_pkg))
