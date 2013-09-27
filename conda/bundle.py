from __future__ import print_function, division, absolute_import

import os
import sys
import json
import hashlib
import tarfile
import tempfile
from os.path import abspath, expanduser, basename, isdir, isfile, islink, join

import conda.config as config
from conda.api import get_index
from conda.misc import untracked
import conda.install as install
import conda.plan as plan


warn = []

BDP = 'bundle-data/'
BMJ = 'bundle-meta.json'

def add_file(t, h, path, f):
    t.add(path, f)
    h.update(f.encode('utf-8'))
    h.update(b'\x00')
    if islink(path):
        link = os.readlink(path)
        h.update(link)
        if link.startswith('/'):
            warn.append('found symlink to absolute path: %s -> %s' % (f, link))
    elif isfile(path):
        h.update(open(path, 'rb').read())
        if path.endswith('.egg-link'):
            warn.append('found egg link: %s' % f)

def add_data(t, h, data_path):
    data_path = abspath(data_path)
    if isfile(data_path):
        f = BDP + basename(data_path)
        add_file(t, h, data_path, f)
    elif isdir(data_path):
        for root, dirs, files in os.walk(data_path):
            for fn in files:
                if fn.endswith(('~', '.pyc')):
                    continue
                path = join(root, fn)
                f = path[len(data_path) + 1:]
                if f.startswith('.git'):
                    continue
                add_file(t, h, path, BDP + f)
    else:
        raise RuntimeError('no such file or directory: %s' % data_path)

def create_bundle(prefix=None, data_path=None, bundle_name=None,
                  extra_meta=None):
    """
    Create a "bundle package" of the environment located in `prefix`,
    and return the full path to the created package.  This file is
    created in a temp directory, and it is the callers responsibility
    to remove this directory (after the file has been handled in some way).
    """
    meta = dict(
        name = bundle_name,
        platform = config.platform,
        arch = config.arch_name,
    )
    tmp_dir = tempfile.mkdtemp()
    tar_path = join(tmp_dir, 'bundle.tar.bz2')
    t = tarfile.open(tar_path, 'w:bz2')
    h = hashlib.new('sha1')
    if prefix:
        prefix = abspath(prefix)
        if not prefix.startswith('/opt/anaconda'):
            for f in sorted(untracked(prefix, exclude_self_build=True)):
                if f.startswith(BDP) or f == BMJ:
                    raise RuntimeError('bad untracked file: %s' % f)
                path = join(prefix, f)
                add_file(t, h, path, f)
        meta['prefix'] = prefix
        meta['linked'] = sorted(install.linked(prefix))

    if data_path:
        add_data(t, h, data_path)

    if extra_meta:
        meta.update(extra_meta)

    meta_path = join(tmp_dir, BMJ)
    with open(meta_path, 'w') as fo:
        json.dump(meta, fo, indent=2, sort_keys=True)
    add_file(t, h, meta_path, BMJ)

    t.close()

    path = join(tmp_dir, 'bundle-%s.tar.bz2' % h.hexdigest())
    os.rename(tar_path, path)
    return path


def clone_bundle(path, prefix=None, bundle_name=None):
    """
    Clone the bundle (located at `path`) by creating a new environment at
    `prefix` (unless prefix is None or the prefix directory already exists)
    """
    t = tarfile.open(path, 'r:*')
    try:
        meta = json.load(t.extractfile(BMJ))
    except KeyError:
        raise RuntimeError("no archive '%s' in: %s" % (BMJ, path))

    if prefix and not isdir(prefix):
        for m in t.getmembers():
            if m.path.startswith(BDP) or m.path == BMJ:
                continue
            t.extract(m, path=prefix)
        actions = plan.ensure_linked_actions(meta.get('linked', []), prefix)
        index = get_index()
        plan.display_actions(actions, index)
        plan.execute_actions(actions, index, verbose=True)

    if not bundle_name:
        bundle_name = meta.get('name')

    bundle_dir = abspath(expanduser('~/bundles/%s' % bundle_name))
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
