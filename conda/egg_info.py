"""
Functions related to core conda functionality that relates to manually
installed Python packages, e.g. using "python setup.py install", or "pip".
"""
from __future__ import absolute_import, print_function

import os
import re
import sys
from os.path import isdir, isfile, join

from conda.compat import itervalues
from conda.install import linked_data
from conda.misc import rel_path



def get_site_packages_dir(installed_pkgs):
    for info in itervalues(installed_pkgs):
        if info['name'] == 'python':
            if sys.platform == 'win32':
                stdlib_dir = 'Lib'
            else:
                py_ver = info['version'][:3]
                stdlib_dir = 'lib/python%s' % py_ver
            return join(stdlib_dir, 'site-packages')
    return None


def get_egg_info_files(sp_dir):
    for fn in os.listdir(sp_dir):
        if not fn.endswith(('.egg', '.egg-info')):
            continue
        path = join(sp_dir, fn)
        if isfile(path):
            yield path
        elif isdir(path):
            for path2 in [join(path, 'PKG-INFO'),
                          join(path, 'EGG-INFO', 'PKG-INFO')]:
                if isfile(path2):
                    yield path2


pat = re.compile(r'(\w+):\s*(\S+)', re.I)
def parse_egg_info(path):
    """
    Parse an .egg-info file and return its canonical distribution name
    """
    info = {}
    for line in open(path):
        line = line.strip()
        m = pat.match(line)
        if m:
            key = m.group(1).lower()
            info[key] = m.group(2)
        try:
            return '%(name)s-%(version)s-<egg_info>' % info
        except KeyError:
            pass
    return None


def get_untracked_egg_info(prefix):
    """
    Retuen the set of all untracked (not conda installed) Python packages,
    by looking at all untracked egg-info files.
    """
    installed_pkgs = linked_data(prefix)
    sp_dir = get_site_packages_dir(installed_pkgs)
    if sp_dir is None:
        return

    conda_files = set()
    for info in itervalues(installed_pkgs):
        conda_files.update(info.get('files', []))

    res = set()
    for path in get_egg_info_files(join(prefix, sp_dir)):
        f = rel_path(prefix, path)
        if f not in conda_files:
            dist = parse_egg_info(path)
            if dist:
                res.add(dist)
    return res


if __name__ == '__main__':
    from pprint import pprint
    pprint(get_untracked_egg_info(sys.prefix))
