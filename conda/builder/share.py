import os
import sys
import json
import hashlib
import tempfile
import shutil
from os.path import basename, isdir, join

import utils
from packup import untracked, create_conda_pkg
from conda.remote import fetch_index, fetch_file
from conda.install import link, linked, get_meta, available, make_available
from conda.config import Config


def get_requires(prefix):
    res = []
    for dist in linked(prefix):
        meta = get_meta(dist, prefix)
        if 'file_hash' not in meta:
            res.append('%(name)s %(version)s %(build)s' % meta)
    res.sort()
    return res

def update_info(info):
    h = hashlib.new('sha1')
    for req in info['requires']:
        h.update(req)
        h.update('\x00')
    h.update(info['file_hash'])
    info['version'] = h.hexdigest()

def create_bundle(prefix):
    """
    Create a "bundle package" of the environment located in `prefix`,
    and return the full path to the created package.  This file is
    created in a temp directory, and it is the callers responsibility
    to remove this directory (after the file has been handled in some way).

    This bundle is a regular meta-package which lists (in its requirements)
    all Anaconda packages installed (not packages the user created manually),
    and all files in the prefix which are not installed from Anaconda
    packages.  When putting this packages into a conda repository,
    it can be used to created a new environment using the conda create
    command.
    """
    info = dict(
        name = 'share',
        build = '0',
        build_number = 0,
        platform = utils.PLATFORM,
        arch = utils.ARCH_NAME,
        requires = get_requires(prefix),
    )
    tmp_dir = tempfile.mkdtemp()
    tmp_path = join(tmp_dir, 'share.tar.bz2')
    create_conda_pkg(prefix, untracked(prefix, exclude_self_build=True),
                     info, tmp_path, update_info)

    path = join(tmp_dir, '%(name)s-%(version)s-%(build)s.tar.bz2' % info)
    os.rename(tmp_path, path)
    return path


def clone_bundle(path, prefix):
    """
    Clone the bundle (located at `path`) by creating a new environment at
    `prefix`.
    """
    pkgs_dir = join(sys.prefix, 'pkgs')
    assert not isdir(prefix)
    assert path.endswith('.tar.bz2')
    dist = basename(path)[:-8]

    avail = available(pkgs_dir)
    if dist not in avail:
        shutil.copyfile(path, join(pkgs_dir, dist + '.tar.bz2'))
        make_available(pkgs_dir, dist)

    with open(join(pkgs_dir, dist, 'info', 'index.json')) as fi:
        meta = json.load(fi)

    channel_urls = Config().channel_urls
    index = fetch_index(channel_urls)

    dists = ['-'.join(r.split()) for r in meta['requires']
             if not r.startswith('conda ')]
    for dist in dists:
        if dist in avail:
            continue
        print "fetching:", dist
        fn = dist + '.tar.bz2'
        if fn in index:
            info = index[fn]
            fetch_file(info['channel'], fn, info['md5'], info['size'])
        else:
            print "WARNING: not index %r" % fn
        make_available(pkgs_dir, dist)

    avail = available(pkgs_dir)
    for dist in dists:
        if dist in avail:
            link(pkgs_dir, dist, prefix)

    os.unlink(join(prefix, 'conda-meta', dist + '.json'))


if __name__ == '__main__':
    path = create_bundle(sys.prefix)
    os.system('tarinfo --si ' + path)
    print path
    clone_bundle(path, join(sys.prefix, 'envs', 'test3'))
