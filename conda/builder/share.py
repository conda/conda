# NOTE:
#     This module is deprecated.  Don't import from this here when writing
#     new code.
from __future__ import print_function, division, absolute_import

import os
import re
import json
import hashlib
import tempfile
import shutil
from os.path import abspath, basename, isdir, join

import conda.config as config
from conda.api import get_index
from conda.misc import untracked
from conda.resolve import MatchSpec
import conda.install as install
import conda.plan as plan

from conda.builder.packup import create_conda_pkg


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

def old_create_bundle(prefix):
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
        platform = config.platform,
        arch = config.arch_name,
        depends = get_requires(prefix),
    )
    tmp_dir = tempfile.mkdtemp()
    tmp_path = join(tmp_dir, 'share.tar.bz2')
    warnings = create_conda_pkg(prefix,
                                untracked(prefix, exclude_self_build=True),
                                info, tmp_path, update_info)

    path = join(tmp_dir, '%(name)s-%(version)s-%(build)s.tar.bz2' % info)
    os.rename(tmp_path, path)
    return path, warnings


def old_clone_bundle(path, prefix):
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
