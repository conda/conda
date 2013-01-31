import os
import re
import sys
import json
import shutil
import tarfile
import tempfile
from os.path import abspath, basename, dirname, islink, join

from conda.config import PACKAGES_DIR
from conda.install import (activated, get_meta, prefix_placeholder,
                           install_local_package)
from conda.naming import split_canonical_name

import utils


def conda_installed_files(prefix):
    """
    Return the set of files which have been installed (using conda) info
    given prefix.
    """
    res = set()
    for dist in activated(prefix):
        meta = get_meta(dist, prefix)
        files = meta['files']
        res.update(set(files))
    return res


def get_installed_version(prefix, name):
    for dist in activated(prefix):
        n, v, b = split_canonical_name(dist)
        if n == name:
            return v
    return None


def rel_path(prefix, path):
    res = path[len(prefix) + 1:]
    if sys.platform == 'win32':
        res = res.replace('\\', '/')
    return res


def walk_prefix(prefix):
    """
    Return the set of all files in a given prefix directory.
    """
    res = set()
    prefix = abspath(prefix)
    ignore = {'pkgs', 'envs', 'conda-meta', 'LICENSE.txt', 'info',
              '.index', '.unionfs'}
    for fn in os.listdir(prefix):
        if fn in ignore:
            continue
        dir_path = join(prefix, fn)
        for root, dirs, files in os.walk(dir_path):
            for fn in files:
                res.add(rel_path(prefix, join(root, fn)))
            for dn in dirs:
                path = join(root, dn)
                if islink(path):
                    res.add(rel_path(prefix, path))
    return res


def untracked(prefix):
    """
    Return (the set) of all untracked files for a given prefix.
    """
    conda_files = conda_installed_files(prefix)
    return {path for path in walk_prefix(prefix) - conda_files
            if not (path.endswith('~') or (path.endswith('.pyc') and
                                           path[:-1] in conda_files))}


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
        platform = utils.PLATFORM,
        arch = utils.ARCH_NAME,
        build_number = int(build_number),
        build = str(build_number),
        requires = [],
    )
    if requires_py:
        d['build'] = ('py%d%d_' % requires_py) + d['build']
        d['requires'].append('python %d.%d' % requires_py)
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
    os.chmod(tmp_path, 0755)
    return True


def make_tarbz2(prefix, name='unknown', version='0.0', build_number=0,
                files=None):
    if files is None:
        files = sorted(untracked(prefix))
    print "Number of files: %d" % len(files)
    if len(files) == 0:
        print "Nothing to package up (no untracked files)."
        return None

    if any('/site-packages/' in f for f in files):
        python_version = get_installed_version(prefix, 'python')
        assert python_version is not None
        requires_py = tuple(int(x) for x in python_version[:3].split('.'))
    else:
        requires_py = False
    info = create_info(name, version, build_number, requires_py)
    tarbz2_fn = '%(name)s-%(version)s-%(build)s.tar.bz2' % info

    has_prefix = []
    tmp_dir = tempfile.mkdtemp()
    t = tarfile.open(tarbz2_fn, 'w:bz2')
    for f in files:
        path = join(prefix, f)
        if f.startswith('bin/') and fix_shebang(tmp_dir, path):
            path = join(tmp_dir, basename(path))
            has_prefix.append(f)
        t.add(path, f)

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

    t.close()
    shutil.rmtree(tmp_dir)
    print '%s created successfully' % tarbz2_fn
    return tarbz2_fn


def guess_pkg_version(files, pkg_name):
    """
    Guess the package version from (usually untracked) files.
    """
    pat = re.compile(r'site-packages[/\\]' + pkg_name + r'-([^\-]+)-', re.I)
    for f in files:
        m = pat.search(f)
        if m:
            return m.group(1)
    return '0.0'


def packup_and_reinstall(prefix, ignore_files, pkg_name, pkg_version=None):
    files = untracked(prefix) - ignore_files
    if pkg_version is None:
        pkg_version = guess_pkg_version(files, pkg_name)
    fn = make_tarbz2(prefix, name=pkg_name, version=pkg_version, files=files)
    if fn is None:
        return
    remove(prefix, files)
    install_local_package(fn, PACKAGES_DIR, prefix)


if __name__ == '__main__':
    make_tarbz2(sys.prefix)
