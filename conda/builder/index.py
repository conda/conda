import os
import json
import tarfile
from os.path import join, getmtime, getsize

from utils import bzip2, md5_file


def file_info(path):
    return dict(size = getsize(path),
                md5 = md5_file(path),
                mtime = getmtime(path))


def read_index_tar(tar_path):
    with tarfile.open(tar_path) as t:
        return json.load(t.extractfile('info/index.json'))


def update_index(dir_path, verbose=False, force=False):
    if verbose:
        print "updating index in:", dir_path
    index_path = join(dir_path, '.index.json')
    if force:
        index = {}
    else:
        try:
            with open(index_path) as fi:
                index = json.load(fi)
        except IOError:
            index = {}

    files = set(fn for fn in os.listdir(dir_path) if fn.endswith('.tar.bz2'))
    for fn in files:
        path = join(dir_path, fn)
        if fn in index and index[fn]['mtime'] == getmtime(path):
            continue
        if verbose:
            print 'updating:', fn
        d = read_index_tar(path)
        d.update(file_info(path))
        index[fn] = d

    # remove files from the index which are not on disk
    for fn in set(index) - files:
        if verbose:
            print "removing:", fn
        del index[fn]

    with open(index_path, 'w') as fo:
        json.dump(index, fo, indent=2, sort_keys=True)

    # --- new repodata
    for fn in index:
        info = index[fn]
        for varname in 'arch', 'platform', 'mtime', 'ucs':
            try:
                del info[varname]
            except KeyError:
                pass

    repodata = dict(
        packages=index,
        info={},
    )
    repodata_path = join(dir_path, 'repodata.json')
    with open(repodata_path, 'w') as fo:
        json.dump(repodata, fo, indent=2, sort_keys=True)
    bzip2(repodata_path)
