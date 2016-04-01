from __future__ import print_function, division, absolute_import

import os
import sys
import json
import time
import shutil
import hashlib
import tarfile
import tempfile
from os.path import abspath, expanduser, basename, isdir, isfile, islink, join

import conda.config as config
from conda.api import get_index
from conda.misc import untracked, discard_conda
import conda.install as install
import conda.plan as plan


ISO8601 = "%Y-%m-%d %H:%M:%S %z"
BDP = 'bundle-data/'

warn = []


def add_file(t, path, f):
    t.add(path, f)
    if islink(path):
        link = os.readlink(path)
        if link.startswith('/'):
            warn.append('found symlink to absolute path: %s -> %s' % (f, link))
    elif isfile(path):
        if path.endswith('.egg-link'):
            warn.append('found egg link: %s' % f)

def add_data(t, data_path):
    data_path = abspath(data_path)
    if isfile(data_path):
        f = BDP + basename(data_path)
        add_file(t, data_path, f)
    elif isdir(data_path):
        for root, dirs, files in os.walk(data_path):
            for fn in files:
                if fn.endswith(('~', '.pyc')):
                    continue
                path = join(root, fn)
                f = path[len(data_path) + 1:]
                if f.startswith('.git'):
                    continue
                add_file(t, path, BDP + f)
    else:
        raise RuntimeError('no such file or directory: %s' % data_path)


def add_info_files(t, meta):
    tmp_dir = tempfile.mkdtemp()
    with open(join(tmp_dir, 'index.json'), 'w') as fo:
        json.dump(meta, fo, indent=2, sort_keys=True)
    with open(join(tmp_dir, 'files'), 'w') as fo:
        for m in t.getmembers():
            fo.write(m.path + '\n')
    for fn in 'index.json', 'files':
        add_file(t, join(tmp_dir, fn), 'info/' + fn)
    shutil.rmtree(tmp_dir)


def get_version(meta):
    s = '%(creator)s:%(bundle_name)s' % meta
    h = hashlib.new('sha1')
    h.update(s.encode('utf-8'))
    return h.hexdigest()


def create_bundle(prefix=None, data_path=None, bundle_name=None,
                  extra_meta=None):
    """
    Create a "bundle" of the environment located in `prefix`,
    and return the full path to the created package, which is going to be
    located in the current working directory, unless specified otherwise.
    """
    meta = dict(
        name='bundle',
        build='0',
        build_number=0,
        type='bundle',
        bundle_name=bundle_name,
        creator=os.getenv('USER'),
        platform=config.platform,
        arch=config.arch_name,
        ctime=time.strftime(ISO8601),
        depends=[],
    )
    meta['version'] = get_version(meta)

    tar_path = join('bundle-%(version)s-0.tar.bz2' % meta)
    t = tarfile.open(tar_path, 'w:bz2')
    if prefix:
        prefix = abspath(prefix)
        if not prefix.startswith('/opt/anaconda'):
            for f in sorted(untracked(prefix, exclude_self_build=True)):
                if f.startswith(BDP):
                    raise RuntimeError('bad untracked file: %s' % f)
                if f.startswith('info/'):
                    continue
                path = join(prefix, f)
                add_file(t, path, f)
        meta['bundle_prefix'] = prefix
        meta['depends'] = [' '.join(dist.rsplit('-', 2)) for dist in
                           sorted(install.linked(prefix))]

    if data_path:
        add_data(t, data_path)

    if extra_meta:
        meta.update(extra_meta)

    add_info_files(t, meta)
    t.close()
    return tar_path


def clone_bundle(path, prefix=None, bundle_name=None):
    """
    Clone the bundle (located at `path`) by creating a new environment at
    `prefix` (unless prefix is None or the prefix directory already exists)
    """
    try:
        t = tarfile.open(path, 'r:*')
        meta = json.load(t.extractfile('info/index.json'))
    except tarfile.ReadError:
        raise RuntimeError('bad tar archive: %s' % path)
    except KeyError:
        raise RuntimeError("no archive 'info/index.json' in: %s" % (path))

    if prefix and not isdir(prefix):
        for m in t.getmembers():
            if m.path.startswith((BDP, 'info/')):
                continue
            t.extract(m, path=prefix)
        dists = discard_conda('-'.join(s.split())
                              for s in meta.get('depends', []))
        actions = plan.ensure_linked_actions(dists, prefix)
        index = get_index()
        plan.display_actions(actions, index)
        plan.execute_actions(actions, index, verbose=True)

    bundle_dir = abspath(expanduser('~/bundles/%s' %
                                    (bundle_name or meta.get('bundle_name'))))
    for m in t.getmembers():
        if m.path.startswith(BDP):
            targetpath = join(bundle_dir, m.path[len(BDP):])
            t._extract_member(m, targetpath)

    t.close()


if __name__ == '__main__':
    try:
        path = sys.argv[1]
    except IndexError:
        path = 'bundle-90809033a16372615e953f6961a6a272a4b35a1a.tar.bz2'
    clone_bundle(path,
                 join(config.envs_dirs[0], 'tc001'))
