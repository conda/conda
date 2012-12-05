import os
import sys
import json
import shutil
import tarfile
import tempfile
from os.path import abspath, islink, join

from conda.install import activated, get_meta

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


def walk_files(dir_path):
    """
    Return the set of all files in a given directory.
    """
    res = set()
    dir_path = abspath(dir_path)
    for root, dirs, files in os.walk(dir_path):
        for fn in files:
            res.add(join(root, fn)[len(dir_path) + 1:])
        for dn in dirs:
            path = join(root, dn)
            if islink(path):
                res.add(path[len(dir_path) + 1:])
    return res


def new_files(prefix):
    conda_files = conda_installed_files(prefix)
    return {path for path in walk_files(prefix) - conda_files
            if not (path.startswith(('pkgs/', 'envs/', 'conda-meta/')) or
                    path.endswith('~') or path == 'LICENSE.txt' or
                    (path.endswith('.pyc') and path[:-1] in conda_files))}


def get_info(files, name, version, build_number):
    if any('site-packages' in f for f in files):
        requires_py = sys.version_info[:2]
    else:
        requires_py = False

    d = dict(
        name = name,
        version = version,
        platform = utils.PLATFORM,
        arch = utils.ARCH_NAME,
        build_number = build_number,
        build = str(build_number),
        requires = [],
    )
    if requires_py:
        d['build'] = ('py%d%d_' % requires_py) + d['build']
        d['requires'].append('python %d.%d' % requires_py)
    return d


def make_tarbz2(prefix, name='unknown', version='0.0', build_number=0):
    files = sorted(new_files(prefix))
    info = get_info(files, name, version, build_number)
    fn = '%(name)s-%(version)s-%(build)s.tar.bz2' % info

    t = tarfile.open(fn, 'w:bz2')
    for f in files:
        t.add(join(prefix, f), f)

    tmp_dir = tempfile.mkdtemp()
    with open(join(tmp_dir, 'files'), 'w') as fo:
        for f in files:
            fo.write(f + '\n')

    with open(join(tmp_dir, 'index.json'), 'w') as fo:
        json.dump(info, fo, indent=2, sort_keys=True)

    t.add(join(tmp_dir, 'files'), 'info/files')
    t.add(join(tmp_dir, 'index.json'), 'info/index.json')
    shutil.rmtree(tmp_dir)
    t.close()


if __name__ == '__main__':
    make_tarbz2(sys.prefix)
