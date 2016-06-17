# NOTE:
#     This module is deprecated.  Don't import from this here when writing
#     new code.
from __future__ import print_function, division, absolute_import

import hashlib
import json
import os
import re
import shutil
import sys
import tarfile
import tempfile
from os.path import basename, isfile, islink, join

from .compat import PY3, itervalues
from .config import platform, arch_name
from .install import prefix_placeholder, linked_data
from .misc import untracked


def get_installed_version(prefix, name):
    for info in itervalues(linked_data(prefix)):
        if info['name'] == name:
            return str(info['version'])
    return None


def create_info(name, version, build_number, requires_py):
    d = dict(
        name=name,
        version=version,
        platform=platform,
        arch=arch_name,
        build_number=int(build_number),
        build=str(build_number),
        depends=[],
    )
    if requires_py:
        d['build'] = ('py%d%d_' % requires_py) + d['build']
        d['depends'].append('python %d.%d*' % requires_py)
    return d


shebang_pat = re.compile(r'^#!.+$', re.M)
def fix_shebang(tmp_dir, path):
    if open(path, 'rb').read(2) != '#!':
        return False

    with open(path) as fi:
        data = fi.read()
    m = shebang_pat.match(data)
    if not (m and 'python' in m.group()):
        return False

    data = shebang_pat.sub('#!%s/bin/python' % prefix_placeholder,
                           data, count=1)
    tmp_path = join(tmp_dir, basename(path))
    with open(tmp_path, 'w') as fo:
        fo.write(data)
    os.chmod(tmp_path, int('755', 8))
    return True


def _add_info_dir(t, tmp_dir, files, has_prefix, info):
    info_dir = join(tmp_dir, 'info')
    os.mkdir(info_dir)
    with open(join(info_dir, 'files'), 'w') as fo:
        for f in files:
            fo.write(f + '\n')

    with open(join(info_dir, 'index.json'), 'w') as fo:
        json.dump(info, fo, indent=2, sort_keys=True)

    if has_prefix:
        with open(join(info_dir, 'has_prefix'), 'w') as fo:
            for f in has_prefix:
                fo.write(f + '\n')

    for fn in os.listdir(info_dir):
        t.add(join(info_dir, fn), 'info/' + fn)


def create_conda_pkg(prefix, files, info, tar_path, update_info=None):
    """
    create a conda package with `files` (in `prefix` and `info` metadata)
    at `tar_path`, and return a list of warning strings
    """
    files = sorted(files)
    warnings = []
    has_prefix = []
    tmp_dir = tempfile.mkdtemp()
    t = tarfile.open(tar_path, 'w:bz2')
    h = hashlib.new('sha1')
    for f in files:
        assert not (f.startswith('/') or f.endswith('/') or
                    '\\' in f or f == ''), f
        path = join(prefix, f)
        if f.startswith('bin/') and fix_shebang(tmp_dir, path):
            path = join(tmp_dir, basename(path))
            has_prefix.append(f)
        t.add(path, f)
        h.update(f.encode('utf-8'))
        h.update(b'\x00')
        if islink(path):
            link = os.readlink(path)
            if PY3 and isinstance(link, str):
                h.update(bytes(link, 'utf-8'))
            else:
                h.update(link)
            if link.startswith('/'):
                warnings.append('found symlink to absolute path: %s -> %s' %
                                (f, link))
        elif isfile(path):
            h.update(open(path, 'rb').read())
            if path.endswith('.egg-link'):
                warnings.append('found egg link: %s' % f)

    info['file_hash'] = h.hexdigest()
    if update_info:
        update_info(info)
    _add_info_dir(t, tmp_dir, files, has_prefix, info)
    t.close()
    shutil.rmtree(tmp_dir)
    return warnings
