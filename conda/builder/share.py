import os
import hashlib
import tempfile
from os.path import basename, join

import utils
from packup import untracked, create_conda_pkg
from conda.install import linked, get_meta


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
    for r in info['requires']:
        h.update(r)
    h.update(info['file_hash'])
    info['name'] = h.hexdigest()

def create_bundle(prefix):
    """
    Create a "bundle package" of the environment located in `prefix`,
    and return the full path to the created package.  This file is
    created in a temp directory, and it is the callers responsibility
    to remove this directory (after the file has been handled in some way).

    This bundle is a meta-package which requires all Anaconda packages
    installed (not packages the user created manually), and all files
    in the prefix which are not installed from Anaconda packages.
    When putting this packages into a conda repository, it can be used
    to created a new environment using the conda create command.
    """
    info = dict(
        version = '0',
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


if __name__ == '__main__':
    import sys
    path = create_bundle(sys.prefix)
    os.system('tarinfo --si ' + path)
    print basename(path)
