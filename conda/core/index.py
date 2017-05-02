# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from itertools import chain
from logging import getLogger

from .linked_data import linked_data
from .package_cache import PackageCache
from ..base.constants import MAX_CHANNEL_PRIORITY
from ..base.context import context
from ..common.compat import iteritems, itervalues
from ..gateways.disk.read import read_index_json
from ..models.channel import Channel, prioritize_channels
from ..models.dist import Dist
from ..models.index_record import EMPTY_LINK, IndexRecord, RepodataRecord
from ..repodata import RepoData

try:
    from cytoolz.itertoolz import take
except ImportError:  # pragma: no cover
    from .._vendor.toolz.itertoolz import take  # NOQA

log = getLogger(__name__)
stdoutlog = getLogger('stdoutlog')


def get_index(channel_urls=(), prepend=True, platform=None,
              use_local=False, use_cache=False, unknown=None, prefix=None):
    """
    Return the index of packages available on the channels

    If prepend=False, only the channels passed in as arguments are used.
    If platform=None, then the current platform is used.
    If prefix is supplied, then the packages installed in that prefix are added.
    """
    if use_local:
        channel_urls = ['local'] + list(channel_urls)
    if prepend:
        channel_urls += context.channels
    if context.offline and unknown is None:
        unknown = True

    subdirs = (platform, 'noarch') if platform is not None else context.subdirs
    channel_priority_map = prioritize_channels(channel_urls, subdirs=subdirs)
    index = fetch_index(channel_priority_map, use_cache=use_cache)

    if prefix or unknown:
        known_channels = {chnl for chnl, _ in itervalues(channel_priority_map)}
    if prefix:
        _supplement_index_with_prefix(index, prefix, known_channels)
    if unknown:
        _supplement_index_with_cache(index, known_channels)
    if context.track_features:
        _supplement_index_with_features(index)
    return index


def fetch_index(channel_urls, use_cache=False, index=None):
    # type: (prioritize_channels(), bool, bool, Dict[Dist, IndexRecord]) -> Dict[Dist, IndexRecord]
    log.debug('channel_urls=' + repr(channel_urls))
    if not context.json:
        stdoutlog.info("Fetching package metadata ...")

    RepoData.clear()  # make sure we start with a clean slateq
    for url, cdata in iteritems(channel_urls):
        RepoData.enable(url, *cdata)
    RepoData.load_all(use_cache)
    # type: List[Sequence[str, Option[Dict[Dist, IndexRecord]]]]
    #   this is sorta a lie; actually more primitve types

    if index is None:
        index = {}
    for url in reversed(RepoData):
        repo = RepoData[url]
        if repo.index:
            index.update(repo.index.get('packages', {}))

    if not context.json:
        stdoutlog.info('\n')
    return index


def _supplement_index_with_prefix(index, prefix, channels):
    # type: (Dict[Dist, IndexRecord], str, Set[canonical_channel]) -> None
    # supplement index with information from prefix/conda-meta
    assert prefix
    maxp = len(channels) + 1
    for dist, info in iteritems(linked_data(prefix)):
        if dist in index:
            # The downloaded repodata takes priority, so we do not overwrite.
            # We do, however, copy the link information so that the solver
            # knows this package is installed.
            old_record = index[dist]
            link = info.get('link') or EMPTY_LINK
            index[dist] = IndexRecord.from_objects(old_record, link=link)
        else:
            # If the package is not in the repodata, use the local data. If
            # the 'depends' field is not present, we need to set it; older
            # installations are likely to have this.
            depends = info.get('depends') or ()
            # If the channel is known but the package is not in the index, it
            # is because 1) the channel is unavailable offline, or 2) it no
            # longer contains this package. Either way, we should prefer any
            # other version of the package to this one. On the other hand, if
            # it is in a channel we don't know about, assign it a value just
            # above the priority of all known channels.
            priority = MAX_CHANNEL_PRIORITY if dist.channel in channels else maxp
            index[dist] = IndexRecord.from_objects(info, depends=depends, priority=priority)


def _supplement_index_with_cache(index, channels):
    # type: (Dict[Dist, IndexRecord], Set[canonical_channel]) -> None
    # supplement index with packages from the cache
    maxp = len(channels) + 1
    for pc_entry in PackageCache.get_all_extracted_entries():
        dist = Dist(pc_entry)
        if dist in index:
            # The downloaded repodata takes priority
            continue
        pkg_dir = pc_entry.extracted_package_dir
        index_json_record = read_index_json(pkg_dir)
        # See the discussion above about priority assignments.
        priority = MAX_CHANNEL_PRIORITY if dist.channel in channels else maxp
        repodata_record = RepodataRecord.from_objects(
            index_json_record,
            fn=dist.to_filename(),
            schannel=dist.channel,
            priority=priority,
            url=dist.to_url(),
        )
        index[dist] = repodata_record


def _supplement_index_with_features(index, features=()):
    defaults = Channel('defaults')
    for feat in chain(context.track_features, features):
        fname = feat + '@'
        rec = IndexRecord(
            name=fname,
            version='0',
            build='0',
            channel=defaults,
            subdir=context.subdir,
            md5="0123456789",
            track_features=feat,
            build_number=0,
            fn=fname)
        index[Dist(rec)] = rec


def dist_str_in_index(index, dist_str):
    return Dist(dist_str) in index
