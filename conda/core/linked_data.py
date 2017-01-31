# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import json
from logging import getLogger
from os import listdir
from os.path import isdir, isfile, join

from ..base.constants import UNKNOWN_CHANNEL
from ..common.compat import itervalues, odict
from ..gateways.disk.delete import rm_rf
from ..models.channel import Channel
from ..models.dist import Dist
from ..models.index_record import EMPTY_LINK, IndexRecord

log = getLogger(__name__)


# Because the conda-meta .json files do not include channel names in
# their filenames, we have to pull that information from the .json
# files themselves. This has made it necessary in virtually all
# circumstances to load the full set of files from this directory.
# Therefore, we have implemented a full internal cache of this
# data to eliminate redundant file reads.
linked_data_ = {}
# type: Dict[Dist, IndexRecord]


def load_linked_data(prefix, dist_name, rec=None, ignore_channels=False):
    meta_file = join(prefix, 'conda-meta', dist_name + '.json')
    if rec is None:
        try:
            log.trace("loading linked data for %s", meta_file)
            with open(meta_file) as fi:
                rec = json.load(fi)
        except IOError:
            return None
    else:
        linked_data(prefix)  # TODO: is this even doing anything?

        if hasattr(rec, 'dump'):
            rec = rec.dump()

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
        if not url or (url.startswith('file:') and channel[0] != UNKNOWN_CHANNEL):
            url = rec['url'] = channel + '/' + fn
    channel, schannel = Channel(url).url_channel_wtf

    rec['url'] = url
    rec['channel'] = channel
    rec['schannel'] = schannel
    rec['link'] = rec.get('link') or EMPTY_LINK

    if ignore_channels:
        dist = Dist.from_string(dist_name)
    else:
        dist = Dist.from_string(dist_name, channel_override=schannel)
    linked_data_[prefix][dist] = rec = IndexRecord(**rec)

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
        recs = linked_data_[prefix] = odict()
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


def set_linked_data(prefix, dist_name, record):
    if prefix in linked_data_:
        load_linked_data(prefix, dist_name, record)


def get_python_version_for_prefix(prefix):
    # returns a string e.g. "2.7", "3.4", "3.5" or None
    py_record_iter = (rcrd for rcrd in itervalues(linked_data(prefix)) if rcrd.name == 'python')
    record = next(py_record_iter, None)
    if record is None:
        return None
    next_record = next(py_record_iter, None)
    if next_record is not None:
        raise RuntimeError("multiple python records found in prefix %s" % prefix)
    else:
        return record.version[:3]
