import os
import json
import base64
import hashlib
import tarfile
from os.path import join, getmtime

from utils import bzip2, file_info


app_meta_path_fmt = 'App/%(name)s/meta.json'

def add_app_metadata(t, info):
    app_meta = json.loads(t.extractfile(app_meta_path_fmt % info).read())
    iconpath = app_meta['icon']
    if iconpath.startswith('./'):
        iconpath = 'App/%s/%s' % (info['name'], iconpath[2:])
    icondata = t.extractfile(iconpath).read()
    info.update(dict(
            type = 'app',
            _icondata = base64.b64encode(icondata),
            icon = hashlib.md5(icondata).hexdigest(),
            summary = app_meta.get('summary'),
    ))

def read_index_tar(tar_path):
    with tarfile.open(tar_path) as t:
        info = json.load(t.extractfile('info/index.json'))
        app_meta_path = app_meta_path_fmt % info
        if any(m.path == app_meta_path for m in t.getmembers()):
            add_app_metadata(t, info)
        return info


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
    icons = {}
    for fn in index:
        info = index[fn]
        if '_icondata' in info:
            icons[info['icon']] = info['_icondata']
        for varname in 'arch', 'platform', 'mtime', 'ucs', '_icondata':
            try:
                del info[varname]
            except KeyError:
                pass

    repodata = {'packages': index, 'icons': icons, 'info': {}}
    repodata_path = join(dir_path, 'repodata.json')
    with open(repodata_path, 'w') as fo:
        json.dump(repodata, fo, indent=2, sort_keys=True)
    bzip2(repodata_path)
