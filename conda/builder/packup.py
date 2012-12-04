import os
from os.path import abspath, islink, join

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
    res = set()
    for path in walk_files(prefix) - conda_files:
        if (path.startswith(('pkgs/', 'envs/', 'conda-meta/'))  or
                  path == 'LICENSE.txt'  or
                  path.endswith('.pyc') and path[:-1] in conda_files):
            continue
        res.add(path)
    return sorted(res)


if __name__ == '__main__':
    import sys
    from pprint import pprint

    pprint(new_files(sys.prefix))
