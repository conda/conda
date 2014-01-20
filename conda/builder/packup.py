from __future__ import print_function, division, absolute_import

import os
import re
import sys
import json
import shutil
import hashlib
import tarfile
import tempfile
from os.path import abspath, basename, dirname, isdir, isfile, islink, join

import conda.config as config
import conda.install as install
from conda.misc import untracked
from conda.compat import PY3


def get_installed_version(prefix, name):
    for dist in install.linked(prefix):
        n, v, b = dist.rsplit('-', 2)
        if n == name:
            return v
    return None


def remove(prefix, files):
    """
    Remove files for a given prefix.
    """
    dst_dirs = set()
    for f in files:
        dst = join(prefix, f)
        dst_dirs.add(dirname(dst))
        os.unlink(dst)

    for path in sorted(dst_dirs, key=len, reverse=True):
        try:
            os.rmdir(path)
        except OSError: # directory might not be empty
            pass


def create_info(name, version, build_number, requires_py):
    d = dict(
        name = name,
        version = version,
        platform = config.platform,
        arch = config.arch_name,
        build_number = int(build_number),
        build = str(build_number),
        depends = [],
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

    data = shebang_pat.sub('#!%s/bin/python' % install.prefix_placeholder,
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


def make_tarbz2(prefix, name='unknown', version='0.0', build_number=0,
                files=None):
    if files is None:
        files = untracked(prefix)
    print("# files: %d" % len(files))
    if len(files) == 0:
        print("# failed: nothing to do")
        return None

    if any('/site-packages/' in f for f in files):
        python_version = get_installed_version(prefix, 'python')
        assert python_version is not None
        requires_py = tuple(int(x) for x in python_version[:3].split('.'))
    else:
        requires_py = False

    info = create_info(name, version, build_number, requires_py)
    tarbz2_fn = '%(name)s-%(version)s-%(build)s.tar.bz2' % info
    create_conda_pkg(prefix, files, info, tarbz2_fn)
    print('# success')
    print(tarbz2_fn)
    return tarbz2_fn


def which_prefix(path):
    """
    given the path (to a (presumably) conda installed file) return the
    environment prefix in which the file in located
    """
    prefix = abspath(path)
    while True:
        if isdir(join(prefix, 'conda-meta')):
            # we found the it, so let's return it
            return prefix
        if prefix == dirname(prefix):
            # we cannot chop off any more directories, so we didn't find it
            return None
        prefix = dirname(prefix)


def which_package(path):
    """
    given the path (of a (presumably) conda installed file) iterate over
    the conda packages the file came from.  Usually the iteration yields
    only one package.
    """
    path = abspath(path)
    prefix = which_prefix(path)
    if prefix is None:
        raise RuntimeError("could not determine conda prefix from: %s" % path)
    for dist in install.linked(prefix):
        meta = install.is_linked(prefix, dist)
        if any(abspath(join(prefix, f)) == path for f in meta['files']):
            yield dist


if __name__ == '__main__':
    make_tarbz2(sys.prefix)
