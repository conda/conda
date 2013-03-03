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
    info.update(dict(
            name = h.hexdigest(),
            version = '0',            
            build_number = 0,
            build = '0',
    ))

def create_bundle(prefix):
    info = dict(requires=get_requires(prefix),
                platform = utils.PLATFORM,
                arch = utils.ARCH_NAME)
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
