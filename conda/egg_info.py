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
from .models.index_record import IndexRecord
from ._vendor.auxlib.exceptions import ValidationError
from .base.constants import PIP_PSEUDOCHANNEL

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


PIP_FIELDS = ('name', 'version')
pat = re.compile(r'(\w+):\s*([^\s:]+)', re.I)
def parse_egg_info(path):
    """
    Parse an .egg-info file and return its canonical distribution name
    """
    info = {'build': '<pip>',
            'build_number': 0,
            'schannel': PIP_PSEUDOCHANNEL}
    for line in open(path, encoding='utf-8'):
        line = line.strip()
        m = pat.match(line)
        if m:
            fld = m.group(1).lower()
            if fld in PIP_FIELDS:
                info[fld] = m.group(2)
    try:
        info['fn'] = '%(name)s-%(version)s-%(build)s' % info
        info = IndexRecord.from_objects(info)
    except (KeyError, ValidationError, UnicodeDecodeError):
        return None
    return info


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

    res = {}
    for path in get_egg_info_files(join(prefix, sp_dir)):
        f = rel_path(prefix, path)
        if not all_pkgs and f in conda_files:
            continue
        info = parse_egg_info(path)
        if info:
            res[Dist(info)] = info
    return res


if __name__ == '__main__':
    from pprint import pprint
    pprint(get_egg_info(sys.prefix))
