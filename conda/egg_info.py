"""
Functions related to core conda functionality that relates to manually
installed Python packages, e.g. using "python setup.py install", or "pip".
"""
from __future__ import absolute_import, division, print_function, unicode_literals

from io import open
import os
from os.path import isdir, isfile, join
import re
import sys

from .common.compat import itervalues, on_win
from .core.linked_data import linked_data
from .misc import rel_path
from .models.dist import Dist


def get_site_packages_dir(installed_pkgs):
    for info in itervalues(installed_pkgs):
        if info['name'] == 'python':
            if on_win:
                stdlib_dir = 'Lib'
            else:
                py_ver = info['version'][:3]
                stdlib_dir = 'lib/python%s' % py_ver
            return join(stdlib_dir, 'site-packages')
    return None


def get_egg_info_files(sp_dir):
    for fn in os.listdir(sp_dir):
        if not fn.endswith(('.egg', '.egg-info', '.dist-info')):
            continue
        path = join(sp_dir, fn)
        if isfile(path):
            yield path
        elif isdir(path):
            for path2 in [join(path, 'PKG-INFO'),
                          join(path, 'EGG-INFO', 'PKG-INFO'),
                          join(path, 'METADATA')]:
                if isfile(path2):
                    yield path2


pat = re.compile(r'(\w+):\s*(\S+)', re.I)
def parse_egg_info(path):
    """
    Parse an .egg-info file and return its canonical distribution name
    """
    info = {}
    for line in open(path, encoding='utf-8'):
        line = line.strip()
        m = pat.match(line)
        if m:
            key = m.group(1).lower()
            info[key] = m.group(2)
        try:
            return '%(name)s-%(version)s-<pip>' % info
        except KeyError:
            pass
    return None


def get_egg_info(prefix, all_pkgs=False):
    """
    Return a set of canonical names of all Python packages (in `prefix`),
    by inspecting the .egg-info files inside site-packages.
    By default, only untracked (not conda installed) .egg-info files are
    considered.  Setting `all_pkgs` to True changes this.
    """
    installed_pkgs = linked_data(prefix)
    sp_dir = get_site_packages_dir(installed_pkgs)
    if sp_dir is None:
        return set()

    conda_files = set()
    for info in itervalues(installed_pkgs):
        conda_files.update(info.get('files', []))

    res = set()
    for path in get_egg_info_files(join(prefix, sp_dir)):
        f = rel_path(prefix, path)
        if all_pkgs or f not in conda_files:
            try:
                dist = parse_egg_info(path)
            except UnicodeDecodeError:
                dist = None
            if dist:
                res.add(Dist(dist))
    return res


if __name__ == '__main__':
    from pprint import pprint
    pprint(get_egg_info(sys.prefix))
