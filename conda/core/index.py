# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from collections import namedtuple
from itertools import chain
from logging import getLogger

from concurrent.futures import as_completed

from .linked_data import linked_data
from .package_cache import PackageCache
from .repodata import SubdirData, make_feature_record
from .._vendor.boltons.setutils import IndexedSet
from ..base.constants import MAX_CHANNEL_PRIORITY
from ..base.context import context
from ..common.compat import iteritems, iterkeys, itervalues, odict
from ..common.io import backdown_thread_pool
from ..exceptions import OperationNotAllowed
from ..gateways.disk.read import read_index_json
from ..models import translate_feature_str
from ..models.channel import Channel, prioritize_channels
from ..models.dist import Dist
from ..models.index_record import EMPTY_LINK, IndexRecord, PackageRecord
from ..models.match_spec import MatchSpec

try:
    from cytoolz.itertoolz import concat, take
except ImportError:  # pragma: no cover
    from .._vendor.toolz.itertoolz import concat, take  # NOQA

log = getLogger(__name__)


def check_whitelist(channel_urls):
    if context.whitelist_channels:
        whitelist_channel_urls = tuple(concat(
            Channel(c).base_urls for c in context.whitelist_channels
        ))
        for url in channel_urls:
            these_urls = Channel(url).base_urls
            if not all(this_url in whitelist_channel_urls for this_url in these_urls):
                bad_channel = Channel(url)
                raise OperationNotAllowed("Channel not included in whitelist:\n"
                                          "  location: %s\n"
                                          "  canonical name: %s\n"
                                          % (bad_channel.location, bad_channel.canonical_name))


def get_index(channel_urls=(), prepend=True, platform=None,
              use_local=False, use_cache=False, unknown=None, prefix=None):
    """
    Return the index of packages available on the channels

    If prepend=False, only the channels passed in as arguments are used.
    If platform=None, then the current platform is used.
    If prefix is supplied, then the packages installed in that prefix are added.
    """
    if context.offline and unknown is None:
        unknown = True

    channel_priority_map = get_channel_priority_map(channel_urls, prepend, platform, use_local)

    check_whitelist(iterkeys(channel_priority_map))

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

    use_cache = use_cache or context.use_index_cache

    # channel_urls reversed to build up index in correct order
    CollectTask = namedtuple('CollectTask', ('url', 'schannel', 'priority'))
    tasks = (CollectTask(url, *channel_urls[url]) for url in reversed(channel_urls))
    from .repodata import collect_all_repodata_as_index
    index = collect_all_repodata_as_index(use_cache, tasks)

    return index


def _supplement_index_with_prefix(index, prefix, channels):
    # type: (Dict[Dist, IndexRecord], str, Set[canonical_channel]) -> None
    # supplement index with information from prefix/conda-meta
    assert prefix
    maxp = len(channels) + 1
    for dist, info in iteritems(linked_data(prefix)):
        if dist in index:
            # The downloaded repodata takes priority, so we do not overwrite.
            # We do, however, copy the link information so that the solver (i.e. resolve)
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
        repodata_record = PackageRecord.from_objects(
            index_json_record,
            fn=dist.to_filename(),
            schannel=dist.channel,
            priority=priority,
            url=dist.to_url(),
        )
        index[dist] = repodata_record


def _supplement_index_with_features(index, features=()):
    for feature in chain(context.track_features, features):
        rec = make_feature_record(*translate_feature_str(feature))
        index[Dist(rec)] = rec


def get_channel_priority_map(channel_urls=(), prepend=True, platform=None, use_local=False):
    if use_local:
        channel_urls = ['local'] + list(channel_urls)
    if prepend:
        channel_urls += context.channels

    subdirs = (platform, 'noarch') if platform is not None else context.subdirs
    channel_priority_map = prioritize_channels(channel_urls, subdirs=subdirs)
    return channel_priority_map


def dist_str_in_index(index, dist_str):
    return Dist(dist_str) in index


def get_reduced_index(prefix, channels, subdirs, specs):

    # TODO: need a "combine" step to consolidate specs

    with backdown_thread_pool() as executor:

        channel_priority_map = odict((k, v[1]) for k, v in
                                     iteritems(prioritize_channels(channels, subdirs=subdirs)))
        subdir_datas = tuple(SubdirData(Channel(url), priority) for url, priority in
                             iteritems(channel_priority_map))

        records = IndexedSet()
        collected_names = set()
        collected_provides_features = set()
        pending_names = set()
        pending_provides_features = set()

        def query_all(spec):
            futures = (executor.submit(sd.query, spec) for sd in subdir_datas)
            return tuple(concat(future.result() for future in as_completed(futures)))

        def push_spec(spec):
            name = spec.get_raw_value('name')
            if name and name not in collected_names:
                pending_names.add(name)
            provides_features = spec.get_raw_value('provides_features')
            if provides_features:
                for ftr_name, ftr_value in iteritems(provides_features):
                    kv_feature = "%s=%s" % (ftr_name, ftr_value)
                    if kv_feature not in collected_provides_features:
                        pending_provides_features.add(kv_feature)

        def push_record(record):
            for _spec in record.combined_depends:
                push_spec(_spec)
            if record.provides_features:
                for ftr_name, ftr_value in iteritems(record.provides_features):
                    kv_feature = "%s=%s" % (ftr_name, ftr_value)
                    push_spec(MatchSpec(provides_features=kv_feature))

        for spec in specs:
            push_spec(spec)

        while pending_names or pending_provides_features:
            while pending_names:
                name = pending_names.pop()
                collected_names.add(name)
                spec = MatchSpec(name)
                new_records = query_all(spec)
                for record in new_records:
                    push_record(record)
                records.update(new_records)

            while pending_provides_features:
                kv_feature = pending_provides_features.pop()
                collected_provides_features.add(kv_feature)
                spec = MatchSpec(provides_features=kv_feature)
                new_records = query_all(spec)
                for record in new_records:
                    push_record(record)
                records.update(new_records)

        reduced_index = {Dist(rec): rec for rec in records}

        known_channels = tuple(Channel(c).canonical_name for c in channels)

        if prefix is not None:
            _supplement_index_with_prefix(reduced_index, prefix, known_channels)

        if context.offline or ('unknown' in context._argparse_args
                               and context._argparse_args.unknown):
            # This is really messed up right now.  Dates all the way back to
            # https://github.com/conda/conda/commit/f761f65a82b739562a0d997a2570e2b8a0bdc783
            # TODO: revisit this later
            _supplement_index_with_cache(reduced_index, known_channels)
        _supplement_index_with_features(reduced_index)

        # TODO: make feature records ???

        return reduced_index
