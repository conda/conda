from __future__ import print_function, division, absolute_import

import os
import re
import sys
import json
import hashlib
import tarfile
import tempfile
import shutil
from logging import getLogger
from os.path import abspath, basename, isdir, isfile, islink, join

import conda.config as config
from conda.api import get_index
from conda.misc import untracked
from conda.resolve import MatchSpec
import conda.install as install
import conda.plan as plan


log = getLogger(__name__)


def get_requires(prefix):
    res = []
    for dist in install.linked(prefix):
        meta = install.is_linked(prefix, dist)
        assert meta
        if 'file_hash' not in meta:
            res.append('%(name)s %(version)s %(build)s' % meta)
    res.sort()
    return res

def update_info(info):
    h = hashlib.new('sha1')
    for spec in info['depends']:
        assert MatchSpec(spec).strictness == 3
        h.update(spec.encode('utf-8'))
        h.update(b'\x00')
    h.update(info['file_hash'].encode('utf-8'))
    info['version'] = h.hexdigest()

def add_hash(h, path, f):
    h.update(f.encode('utf-8'))
    h.update(b'\x00')
    if islink(path):
        link = os.readlink(path)
        h.update(link)
        if link.startswith('/'):
            log.warn('found symlink to absolute path: %s -> %s' % (f, link))
    elif isfile(path):
        h.update(open(path, 'rb').read())
        if path.endswith('.egg-link'):
            log.warn('found egg link: %s' % f)

def add_data(t, h, data_path):
    data_path = abspath(data_path)
    if isfile(data_path):
        f = 'bundle/' + basename(data_path)
        t.add(data_path, f)
        add_hash(h, data_path, f)
    elif isdir(data_path):
        for root, dirs, files in os.walk(data_path):
            for fn in files:
                if fn.endswith(('~', '.pyc')):
                    continue
                path = join(root, fn)
                f = 'bundle/' + path[len(data_path) + 1:]
                t.add(path, f)
                add_hash(h, path, f)
    else:
        raise RuntimeError('no such file or directory: %s' % data_path)

def create_bundle(prefix, data_path=None):
    """
    Create a "bundle package" of the environment located in `prefix`,
    and return the full path to the created package.  This file is
    created in a temp directory, and it is the callers responsibility
    to remove this directory (after the file has been handled in some way).
    """
    tmp_dir = tempfile.mkdtemp()
    tar_path = join(tmp_dir, 'bundle.tar.bz2')
    t = tarfile.open(tar_path, 'w:bz2')
    h = hashlib.new('sha1')
    for f in sorted(untracked(prefix, exclude_self_build=True)):
        path = join(prefix, f)
        t.add(path, f)
        add_hash(h, path, f)

    if data_path:
        add_data(t, h, data_path)

    print('h:', h.hexdigest())
    t.close()
    print('tar_path:', tar_path)

    sys.exit(0)

    info = dict(
        name = 'share',
        build = '0',
        build_number = 0,
        platform = config.platform,
        arch = config.arch_name,
        depends = get_requires(prefix),
    )

    path = join(tmp_dir, '%(name)s-%(version)s-%(build)s.tar.bz2' % info)
    os.rename(tar_path, path)
    return path


def clone_bundle(path, prefix):
    """
    Clone the bundle (located at `path`) by creating a new environment at
    `prefix`.
    The directory `path` is located in should be some temp directory or
    some other directory OUTSITE /opt/anaconda (this function handles
    copying the of the file if necessary for you).  After calling this
    funtion, the original file (at `path`) may be removed.
    """
    assert not abspath(path).startswith(abspath(config.root_dir))
    assert not isdir(prefix)
    fn = basename(path)
    assert re.match(r'share-[0-9a-f]{40}-\d+\.tar\.bz2$', fn), fn
    dist = fn[:-8]

    pkgs_dir = config.pkgs_dirs[0]
    if not install.is_extracted(pkgs_dir, dist):
        shutil.copyfile(path, join(pkgs_dir, dist + '.tar.bz2'))
        plan.execute_plan(['%s %s' % (plan.EXTRACT, dist)])
    assert install.is_extracted(pkgs_dir, dist)

    with open(join(pkgs_dir, dist, 'info', 'index.json')) as fi:
        meta = json.load(fi)

    # for backwards compatibility, use "requires" when "depends" is not there
    dists = ['-'.join(r.split())
             for r in meta.get('depends', meta.get('requires', []))
             if not r.startswith('conda ')]
    dists.append(dist)

    actions = plan.ensure_linked_actions(dists, prefix)
    index = get_index()
    plan.display_actions(actions, index)
    plan.execute_actions(actions, index, verbose=True)

    os.unlink(join(prefix, 'conda-meta', dist + '.json'))


if __name__ == '__main__':
    #path, warnings = create_bundle(config.root_dir)
    #print(warnings)
    #os.system('tarinfo --si ' + path)
    #path = ('/Users/ilan/src/'
    #        'share-fffeff0d78414137f40fff7065c1cfc77f0dd317-0.tar.bz2')
    #clone_bundle(path, join(config.envs_dirs[0], 'test3'))
    pass
