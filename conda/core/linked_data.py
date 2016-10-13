# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import json
from logging import getLogger
from os import listdir, makedirs
from os.path import isdir, isfile, join

from .package_cache import read_url
from .._vendor.auxlib.entity import EntityEncoder
from ..base.constants import UTF8
from ..common.disk import rm_rf, yield_lines
from ..models.channel import Channel
from ..models.dist import Dist
from ..models.record import EMPTY_LINK, Link, Record

log = getLogger(__name__)


# Because the conda-meta .json files do not include channel names in
# their filenames, we have to pull that information from the .json
# files themselves. This has made it necessary in virtually all
# circumstances to load the full set of files from this directory.
# Therefore, we have implemented a full internal cache of this
# data to eliminate redundant file reads.
linked_data_ = {}


def load_linked_data(prefix, dist_name, rec=None, ignore_channels=False):
    meta_file = join(prefix, 'conda-meta', dist_name + '.json')
    if rec is None:
        try:
            with open(meta_file) as fi:
                rec = Record(**json.load(fi))
        except IOError:
            return None
    else:
        linked_data(prefix)  # TODO: is this even doing anything?
    url = rec.get('url')
    fn = rec.get('fn')
    if not fn:
        fn = rec['fn'] = url.rsplit('/', 1)[-1] if url else dist_name + '.tar.bz2'
    if fn[:-8] != dist_name:
        log.debug('Ignoring invalid package metadata file: %s' % meta_file)
        return None
    channel = rec.get('channel')
    if channel:
        channel = channel.rstrip('/')
        if not url or (url.startswith('file:') and channel[0] != '<unknown>'):
            url = rec['url'] = channel + '/' + fn
    channel, schannel = Channel(url).url_channel_wtf
    rec['url'] = url
    rec['channel'] = channel
    rec['schannel'] = schannel
    rec['link'] = rec.get('link') or EMPTY_LINK

    d = Dist(dist_name)
    if ignore_channels:
        dist = Dist(channel=None, package_name=d.package_name, version=d.version,
                    build_string=d.build_string)
    else:
        dist = Dist(channel=schannel, package_name=d.package_name, version=d.version,
                    build_string=d.build_string)
    linked_data_[prefix][dist] = rec

    return rec


def delete_linked_data(prefix, dist, delete=True):
    recs = linked_data_.get(prefix)
    if recs and dist in recs:
        del recs[dist]
    if delete:
        meta_path = join(prefix, 'conda-meta', dist.to_filename('.json'))
        if isfile(meta_path):
            rm_rf(meta_path)


def delete_prefix_from_linked_data(path):
    '''Here, path may be a complete prefix or a dist inside a prefix'''
    linked_data_path = next((key for key in sorted(linked_data_.keys(), reverse=True)
                             if path.startswith(key)),
                            None)
    if linked_data_path:
        del linked_data_[linked_data_path]
        return True
    return False


def load_meta(prefix, dist):
    """
    Return the install meta-data for a linked package in a prefix, or None
    if the package is not linked in the prefix.
    """
    return linked_data(prefix).get(dist)


def linked_data(prefix, ignore_channels=False):
    """
    Return a dictionary of the linked packages in prefix.
    """
    # Manually memoized so it can be updated
    recs = linked_data_.get(prefix)
    if recs is None:
        recs = linked_data_[prefix] = {}
        meta_dir = join(prefix, 'conda-meta')
        if isdir(meta_dir):
            for fn in listdir(meta_dir):
                if fn.endswith('.json'):
                    dist_name = fn[:-5]
                    load_linked_data(prefix, dist_name, ignore_channels=ignore_channels)
    return recs


def linked(prefix, ignore_channels=False):
    """
    Return the set of canonical names of linked packages in prefix.
    """
    return set(linked_data(prefix, ignore_channels=ignore_channels).keys())


def is_linked(prefix, dist):
    """
    Return the install metadata for a linked package in a prefix, or None
    if the package is not linked in the prefix.
    """
    # FIXME Functions that begin with `is_` should return True/False
    return load_meta(prefix, dist)


def read_icondata(source_dir):
    import base64

    try:
        data = open(join(source_dir, 'info', 'icon.png'), 'rb').read()
        return base64.b64encode(data).decode(UTF8)
    except IOError:
        pass
    return None


def create_meta(prefix, dist, source_dir, index, files, linktype):
    """
    Create the conda metadata, in a given prefix, for a given package.
    """
    from conda.install import link_name_map

    meta_dict = index.get(dist, {})
    meta_dict['url'] = read_url(dist)
    alt_files_path = join(prefix, 'conda-meta', dist.to_filename('.files'))
    if isfile(alt_files_path):
        # alt_files_path is a hack for noarch
        meta_dict['files'] = list(yield_lines(alt_files_path))
    else:
        meta_dict['files'] = files
    meta_dict['link'] = Link(source=source_dir, type=link_name_map.get(linktype))
    if 'icon' in meta_dict:
        meta_dict['icondata'] = read_icondata(source_dir)

    # read info/index.json first
    with open(join(source_dir, 'info', 'index.json')) as fi:
        meta = Record(**json.load(fi))  # TODO: change to LinkedPackageData

    meta.update(meta_dict)

    # add extra info, add to our internal cache
    if not meta.get('url'):
        meta['url'] = read_url(dist)

    # write into <env>/conda-meta/<dist>.json
    meta_dir = join(prefix, 'conda-meta')
    if not isdir(meta_dir):
        makedirs(meta_dir)
    with open(join(meta_dir, dist.to_filename('.json')), 'w') as fo:
        json.dump(meta, fo, indent=2, sort_keys=True, cls=EntityEncoder)

    # update in-memory cache
    if prefix in linked_data_:
        load_linked_data(prefix, dist.dist_name, meta)
