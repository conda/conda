from __future__ import print_function, division, absolute_import

import os
import bz2
import json
import base64
import hashlib
import tarfile
from os.path import isdir, join, getmtime

from utils import file_info



def read_index_tar(tar_path):
    with tarfile.open(tar_path) as t:
        info = json.load(t.extractfile('info/index.json'))
        try:
            raw = t.extractfile('info/icon.png').read()
            info['_icondata'] = base64.b64encode(raw)
            info['_iconmd5'] = hashlib.md5(raw).hexdigest()
        except KeyError:
            pass
        return info

def write_repodata(repodata, dir_path):
    data = json.dumps(repodata, indent=2, sort_keys=True)
    # strip trailing whitespace
    data = '\n'.join(line.rstrip() for line in data.split('\n'))
    # make sure we have newline at the end
    if not data.endswith('\n'):
        data += '\n'
    with open(join(dir_path, 'repodata.json'), 'w') as fo:
        fo.write(data)
    with open(join(dir_path, 'repodata.json.bz2'), 'wb') as fo:
        fo.write(bz2.compress(data))

def update_index(dir_path, verbose=False, force=False):
    if verbose:
        print("updating index in:", dir_path)
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
            print('updating:', fn)
        d = read_index_tar(path)
        d.update(file_info(path))
        index[fn] = d

    # remove files from the index which are not on disk
    for fn in set(index) - files:
        if verbose:
            print("removing:", fn)
        del index[fn]

    with open(index_path, 'w') as fo:
        json.dump(index, fo, indent=2, sort_keys=True)

    # --- new repodata
    icons = {}
    for fn in index:
        info = index[fn]
        if '_icondata' in info:
            icons[info['_iconmd5']] = base64.b64decode(info['_icondata'])
            assert '%(_iconmd5)s.png' % info == info['icon']
        for varname in ('arch', 'platform', 'mtime', 'ucs',
                        '_icondata', '_iconmd5'):
            try:
                del info[varname]
            except KeyError:
                pass
    if icons:
        icons_dir = join(dir_path, 'icons')
        if not isdir(icons_dir):
            os.mkdir(icons_dir)
        for md5, raw in icons.iteritems():
            with open(join(icons_dir, '%s.png' % md5), 'wb') as fo:
                fo.write(raw)

    repodata = {'packages': index, 'info': {}}
    write_repodata(repodata, dir_path)
