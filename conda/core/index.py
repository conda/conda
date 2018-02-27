# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from itertools import chain
from logging import getLogger

from .package_cache_data import PackageCacheData
from .prefix_data import PrefixData, linked_data
from .subdir_data import SubdirData, make_feature_record
from .._vendor.boltons.setutils import IndexedSet
from ..base.context import context
from ..common.compat import iteritems, itervalues
from ..common.io import ThreadLimitedThreadPoolExecutor, as_completed, time_recorder
from ..exceptions import OperationNotAllowed
from ..models.channel import Channel, all_channel_urls
from ..models.dist import Dist
from ..models.match_spec import MatchSpec
from ..models.records import EMPTY_LINK, PackageCacheRecord, PrefixRecord
from ..resolve import dashlist

try:
    from cytoolz.itertoolz import concat, concatv, groupby, take
except ImportError:  # pragma: no cover
    from .._vendor.toolz.itertoolz import concat, concatv, groupby, take  # NOQA

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


LAST_CHANNEL_URLS = []

@time_recorder("get_index")
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

    channel_urls = calculate_channel_urls(channel_urls, prepend, platform, use_local)
    del LAST_CHANNEL_URLS[:]
    LAST_CHANNEL_URLS.extend(channel_urls)

    check_whitelist(channel_urls)

    index = fetch_index(channel_urls, use_cache=use_cache)

    if prefix:
        _supplement_index_with_prefix(index, prefix)
    if unknown:
        _supplement_index_with_cache(index)
    if context.track_features:
        _supplement_index_with_features(index)
    return index


def fetch_index(channel_urls, use_cache=False, index=None):
    log.debug('channel_urls=' + repr(channel_urls))

    use_cache = use_cache or context.use_index_cache

    # channel_urls reversed to build up index in correct order
    from .subdir_data import collect_all_repodata_as_index
    index = collect_all_repodata_as_index(use_cache, channel_urls)

    return index


def _supplement_index_with_prefix(index, prefix):
    # supplement index with information from prefix/conda-meta
    assert prefix
    for dist, prefix_record in iteritems(linked_data(prefix)):
        if dist in index:
            # The downloaded repodata takes priority, so we do not overwrite.
            # We do, however, copy the link information so that the solver (i.e. resolve)
            # knows this package is installed.
            current_record = index[dist]
            link = prefix_record.get('link') or EMPTY_LINK
            index[dist] = PrefixRecord.from_objects(current_record, prefix_record, link=link)
        else:
            # If the package is not in the repodata, use the local data.
            # If the channel is known but the package is not in the index, it
            # is because 1) the channel is unavailable offline, or 2) it no
            # longer contains this package. Either way, we should prefer any
            # other version of the package to this one. On the other hand, if
            # it is in a channel we don't know about, assign it a value just
            # above the priority of all known channels.
            index[dist] = prefix_record


def _supplement_index_with_cache(index):
    # supplement index with packages from the cache
    for pcrec in PackageCacheData.get_all_extracted_entries():
        dist = Dist(pcrec)
        if dist in index:
            # The downloaded repodata takes priority
            current_record = index[dist]
            index[dist] = PackageCacheRecord.from_objects(current_record, pcrec)
        else:
            index[dist] = pcrec


def _supplement_index_with_features(index, features=()):
    for feature in chain(context.track_features, features):
        rec = make_feature_record(feature)
        index[Dist(rec)] = rec


def calculate_channel_urls(channel_urls=(), prepend=True, platform=None, use_local=False):
    if use_local:
        channel_urls = ['local'] + list(channel_urls)
    if prepend:
        channel_urls += context.channels

    subdirs = (platform, 'noarch') if platform is not None else context.subdirs
    return all_channel_urls(channel_urls, subdirs=subdirs)


def dist_str_in_index(index, dist_str):
    return Dist(dist_str) in index


def get_reduced_index(prefix, channels, subdirs, specs):

    # # this block of code is a "combine" step intended to filter out redundant specs
    # # causes a problem with py.test tests/core/test_solve.py -k broken_install
    # specs_map = defaultdict(list)
    # for spec in specs:
    #     specs_map[spec.name].append(spec)
    # consolidated_specs = set()
    # for spec_name, specs_group in iteritems(specs_map):
    #     if len(specs_group) == 1:
    #         consolidated_specs.add(specs_group[0])
    #     elif spec_name == '*':
    #         consolidated_specs.update(specs_group)
    #     else:
    #         keep_specs = []
    #         for spec in specs_group:
    #             if len(spec._match_components) > 1 or spec.target or spec.optional:
    #                 keep_specs.append(spec)
    #         consolidated_specs.update(keep_specs)

    with ThreadLimitedThreadPoolExecutor() as executor:

        channel_urls = all_channel_urls(channels, subdirs=subdirs)
        check_whitelist(channel_urls)

        if context.offline:
            grouped_urls = groupby(lambda url: url.startswith('file://'), channel_urls)
            ignored_urls = grouped_urls.get(False, ())
            if ignored_urls:
                log.info("Ignoring the following channel urls because mode is offline.%s",
                         dashlist(ignored_urls))
            channel_urls = IndexedSet(grouped_urls.get(True, ()))
        subdir_datas = tuple(SubdirData(Channel(url)) for url in channel_urls)

        records = IndexedSet()
        collected_names = set()
        collected_track_features = set()
        pending_names = set()
        pending_track_features = set()

        def query_all(spec):
            futures = tuple(executor.submit(sd.query, spec) for sd in subdir_datas)
            return tuple(concat(future.result() for future in as_completed(futures)))

        def push_spec(spec):
            name = spec.get_raw_value('name')
            if name and name not in collected_names:
                pending_names.add(name)
            track_features = spec.get_raw_value('track_features')
            if track_features:
                for ftr_name in track_features:
                    if ftr_name not in collected_track_features:
                        pending_track_features.add(ftr_name)

        def push_record(record):
            push_spec(MatchSpec(record.name))
            for _spec in record.combined_depends:
                push_spec(_spec)
            if record.track_features:
                for ftr_name in record.track_features:
                    push_spec(MatchSpec(track_features=ftr_name))

        if prefix:
            for prefix_rec in PrefixData(prefix).iter_records():
                push_record(prefix_rec)
        for spec in specs:
            push_spec(spec)

        while pending_names or pending_track_features:
            while pending_names:
                name = pending_names.pop()
                collected_names.add(name)
                spec = MatchSpec(name)
                new_records = query_all(spec)
                for record in new_records:
                    push_record(record)
                records.update(new_records)

            while pending_track_features:
                feature_name = pending_track_features.pop()
                collected_track_features.add(feature_name)
                spec = MatchSpec(track_features=feature_name)
                new_records = query_all(spec)
                for record in new_records:
                    push_record(record)
                records.update(new_records)

        reduced_index = {Dist(rec): rec for rec in records}

        if prefix is not None:
            _supplement_index_with_prefix(reduced_index, prefix)

        if context.offline or ('unknown' in context._argparse_args
                               and context._argparse_args.unknown):
            # This is really messed up right now.  Dates all the way back to
            # https://github.com/conda/conda/commit/f761f65a82b739562a0d997a2570e2b8a0bdc783
            # TODO: revisit this later
            _supplement_index_with_cache(reduced_index)

        # add feature records for the solver
        known_features = set()
        for rec in itervalues(reduced_index):
            known_features.update(concatv(rec.track_features, rec.features))
        known_features.update(context.track_features)
        for ftr_str in known_features:
            rec = make_feature_record(ftr_str)
            reduced_index[Dist(rec)] = rec

        return reduced_index
