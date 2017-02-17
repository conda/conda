# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from collections import namedtuple
from itertools import chain
from logging import getLogger

from .linked_data import linked_data
from .package_cache import PackageCache
from .repodata import collect_all_repodata
from ..base.constants import MAX_CHANNEL_PRIORITY
from ..base.context import context
from ..common.compat import iteritems, itervalues
from ..common.url import join_url
from ..gateways.disk.read import read_index_json
from ..models.channel import prioritize_channels
from ..models.dist import Dist
from ..models.index_record import EMPTY_LINK, IndexRecord
from ..resolve import MatchSpec

try:
    from cytoolz.itertoolz import take
except ImportError:
    from .._vendor.toolz.itertoolz import take  # NOQA

log = getLogger(__name__)
stdoutlog = getLogger('stdoutlog')


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
        dist = pc_entry.dist
        if dist in index:
            # The downloaded repodata takes priority
            continue
        pkg_dir = pc_entry.extracted_package_dir
        index_json_record = read_index_json(pkg_dir)
        # See the discussion above about priority assignments.
        priority = MAX_CHANNEL_PRIORITY if dist.channel in channels else maxp
        index_json_record.fn = dist.to_filename()
        index_json_record.schannel = dist.channel
        index_json_record.priority = priority
        index_json_record.url = dist.to_url()
        index[dist] = index_json_record


def supplement_index_with_repodata(index, repodata, channel, priority):
    repodata_info = repodata.get('info', {})
    arch = repodata_info.get('arch')
    platform = repodata_info.get('platform')
    schannel = channel.canonical_name
    channel_url = channel.url()
    auth = channel.auth
    for fn, info in iteritems(repodata['packages']):
        rec = IndexRecord.from_objects(info,
                                       fn=fn,
                                       arch=arch,
                                       platform=platform,
                                       schannel=schannel,
                                       channel=channel_url,
                                       priority=priority,
                                       url=join_url(channel_url, fn),
                                       auth=auth)
        dist = Dist(rec)
        index[dist] = rec
        if 'with_features_depends' in info:
            base_deps = info.get('depends', ())
            base_feats = set(info.get('features', '').strip().split())
            for feat, deps in iteritems(info['with_features_depends']):
                feat = set(feat.strip().split())
                snames = {MatchSpec(s).name for s in deps}
                base2 = [s for s in base_deps if MatchSpec(s).name not in snames]
                feat2 = ' '.join(sorted(base_feats | feat))
                feat = ' '.join(sorted(feat))
                deps2 = base2 + deps
                dist = Dist.from_objects(dist, with_features_depends=feat)
                rec2 = IndexRecord.from_objects(rec, features=feat2, depends=deps2)
                index[dist] = rec2


def supplement_index_with_features(index, features=()):
    for feat in chain(context.track_features, features):
        fname = feat + '@'
        rec = IndexRecord(
            name=fname,
            version='0',
            build='0',
            schannel='defaults',
            track_features=feat,
            build_number=0,
            fn=fname)
        index[Dist(rec)] = rec


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

    channel_priority_map = prioritize_channels(channel_urls, platform=platform)
    index = fetch_index(channel_priority_map, use_cache=use_cache)

    if prefix or unknown:
        known_channels = {chnl for chnl, _ in itervalues(channel_priority_map)}
    if prefix:
        _supplement_index_with_prefix(index, prefix, known_channels)
    if unknown:
        _supplement_index_with_cache(index, known_channels)
    if context.track_features:
        supplement_index_with_features(index)
    return index


def fetch_index(channel_urls, use_cache=False, index=None):
    # type: (prioritize_channels(), bool, bool, Dict[Dist, IndexRecord]) -> Dict[Dist, IndexRecord]
    log.debug('channel_urls=' + repr(channel_urls))
    if not context.json:
        stdoutlog.info("Fetching package metadata ...")

    CollectTask = namedtuple('CollectTask', ('url', 'schannel', 'priority'))
    tasks = [CollectTask(url, *cdata) for url, cdata in iteritems(channel_urls)]
    repodatas = collect_all_repodata(use_cache, tasks)
    # type: List[Sequence[str, Option[Dict[Dist, IndexRecord]]]]
    #   this is sorta a lie; actually more primitve types

    if index is None:
        index = {}
    for _, repodata in repodatas:
        if repodata:
            index.update(repodata.get('packages', {}))

    if not context.json:
        stdoutlog.info('\n')
    return index


def dist_str_in_index(index, dist_str):
    return Dist(dist_str) in index
