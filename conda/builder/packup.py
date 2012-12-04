import os
import json
import shutil
import tarfile
import tempfile
from os.path import abspath, basename, islink, join

from conda.install import activated, get_meta


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


def get_info(dist):
    d = {}
    d['name'], d['version'], d['build'] = dist.rsplit('-', 2)
    return d


def make_tarbz2(prefix, tarbz2_path):
    assert tarbz2_path.endswith('.tar.bz2')
    files = sorted(new_files(prefix))

    t = tarfile.open(tarbz2_path, 'w:bz2')
    for f in files:
        t.add(join(prefix, f), f)

    tmp_dir = tempfile.mkdtemp()
    with open(join(tmp_dir, 'files'), 'w') as fo:
        for f in files:
            fo.write(f + '\n')

    with open(join(tmp_dir, 'index.json'), 'w') as fo:
        json.dump(get_info(basename(tarbz2_path)[:-8]),
                  fo, indent=2, sort_keys=True)

    t.add(join(tmp_dir, 'files'), 'info/files')
    t.add(join(tmp_dir, 'index.json'), 'info/index.json')
    shutil.rmtree(tmp_dir)
    t.close()


if __name__ == '__main__':
    import sys
    #from pprint import pprint
    #pprint(new_files(sys.prefix))
    make_tarbz2(sys.prefix, 'xyz-1.0-0.tar.bz2')
