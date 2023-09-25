# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Tools for fetching the current index."""
import platform
import sys
from itertools import chain
from logging import getLogger

try:
    from boltons.setutils import IndexedSet
except ImportError:  # pragma: no cover
    from .._vendor.boltons.setutils import IndexedSet

from ..base.context import context
from ..common.io import ThreadLimitedThreadPoolExecutor, time_recorder
from ..exceptions import ChannelNotAllowed, InvalidSpec
from ..gateways.logging import initialize_logging
from ..models.channel import Channel, all_channel_urls
from ..models.enums import PackageType
from ..models.match_spec import MatchSpec
from ..models.records import EMPTY_LINK, PackageCacheRecord, PackageRecord, PrefixRecord
from .package_cache_data import PackageCacheData
from .prefix_data import PrefixData
from .subdir_data import SubdirData, make_feature_record

log = getLogger(__name__)


def check_allowlist(channel_urls):
    if context.allowlist_channels:
        allowlist_channel_urls = tuple(
            chain.from_iterable(
                Channel(c).base_urls for c in context.allowlist_channels
            )
        )
        for url in channel_urls:
            these_urls = Channel(url).base_urls
            if not all(this_url in allowlist_channel_urls for this_url in these_urls):
                raise ChannelNotAllowed(Channel(url))


LAST_CHANNEL_URLS = []


@time_recorder("get_index")
def get_index(
    channel_urls=(),
    prepend=True,
    platform=None,
    use_local=False,
    use_cache=False,
    unknown=None,
    prefix=None,
    repodata_fn=context.repodata_fns[-1],
):
    """
    Return the index of packages available on the channels

    If prepend=False, only the channels passed in as arguments are used.
    If platform=None, then the current platform is used.
    If prefix is supplied, then the packages installed in that prefix are added.
    """
    initialize_logging()  # needed in case this function is called directly as a public API

    if context.offline and unknown is None:
        unknown = True

    channel_urls = calculate_channel_urls(channel_urls, prepend, platform, use_local)
    LAST_CHANNEL_URLS.clear()
    LAST_CHANNEL_URLS.extend(channel_urls)

    check_allowlist(channel_urls)

    index = fetch_index(channel_urls, use_cache=use_cache, repodata_fn=repodata_fn)

    if prefix:
        _supplement_index_with_prefix(index, prefix)
    if unknown:
        _supplement_index_with_cache(index)
    if context.track_features:
        _supplement_index_with_features(index)
    return index


def fetch_index(
    channel_urls, use_cache=False, index=None, repodata_fn=context.repodata_fns[-1]
):
    log.debug("channel_urls=" + repr(channel_urls))
    index = {}
    with ThreadLimitedThreadPoolExecutor() as executor:
        subdir_instantiator = lambda url: SubdirData(
            Channel(url), repodata_fn=repodata_fn
        )
        for f in executor.map(subdir_instantiator, channel_urls):
            index.update((rec, rec) for rec in f.iter_records())
    return index


def dist_str_in_index(index, dist_str):
    match_spec = MatchSpec.from_dist_str(dist_str)
    return any(match_spec.match(prec) for prec in index.values())


def _supplement_index_with_prefix(index, prefix):
    # supplement index with information from prefix/conda-meta
    assert prefix
    for prefix_record in PrefixData(prefix).iter_records():
        if prefix_record in index:
            current_record = index[prefix_record]
            if current_record.channel == prefix_record.channel:
                # The downloaded repodata takes priority, so we do not overwrite.
                # We do, however, copy the link information so that the solver (i.e. resolve)
                # knows this package is installed.
                link = prefix_record.get("link") or EMPTY_LINK
                index[prefix_record] = PrefixRecord.from_objects(
                    current_record, prefix_record, link=link
                )
            else:
                # If the local packages channel information does not agree with
                # the channel information in the index then they are most
                # likely referring to different packages.  This can occur if a
                # multi-channel changes configuration, e.g. defaults with and
                # without the free channel. In this case we need to fake the
                # channel data for the existing package.
                prefix_channel = prefix_record.channel
                prefix_channel._Channel__canonical_name = prefix_channel.url()
                del prefix_record._PackageRecord__pkey
                index[prefix_record] = prefix_record
        else:
            # If the package is not in the repodata, use the local data.
            # If the channel is known but the package is not in the index, it
            # is because 1) the channel is unavailable offline, or 2) it no
            # longer contains this package. Either way, we should prefer any
            # other version of the package to this one. On the other hand, if
            # it is in a channel we don't know about, assign it a value just
            # above the priority of all known channels.
            index[prefix_record] = prefix_record


def _supplement_index_with_cache(index):
    # supplement index with packages from the cache
    for pcrec in PackageCacheData.get_all_extracted_entries():
        if pcrec in index:
            # The downloaded repodata takes priority
            current_record = index[pcrec]
            index[pcrec] = PackageCacheRecord.from_objects(current_record, pcrec)
        else:
            index[pcrec] = pcrec


def _make_virtual_package(name, version=None, build_string=None):
    return PackageRecord(
        package_type=PackageType.VIRTUAL_SYSTEM,
        name=name,
        version=version or "0",
        build_string=build_string or "0",
        channel="@",
        subdir=context.subdir,
        md5="12345678901234567890123456789012",
        build_number=0,
        fn=name,
    )


def _supplement_index_with_features(index, features=()):
    for feature in chain(context.track_features, features):
        rec = make_feature_record(feature)
        index[rec] = rec


def _supplement_index_with_system(index):
    """
    Loads and populates virtual package records from conda plugins
    and adds them to the provided index, unless there is a naming
    conflict.
    """
    for package in context.plugin_manager.get_virtual_packages():
        rec = _make_virtual_package(f"__{package.name}", package.version, package.build)
        index[rec] = rec


def get_archspec_name():
    from conda.base.context import _arch_names, _platform_map, non_x86_machines

    target_plat, target_arch = context.subdir.split("-")
    # This has to reverse what Context.subdir is doing
    if target_arch in non_x86_machines:
        machine = target_arch
    elif target_arch == "zos":
        return None
    elif target_arch.isdigit():
        machine = _arch_names[int(target_arch)]
    else:
        return None

    # This has to match what Context.platform is doing
    native_plat = _platform_map.get(sys.platform, "unknown")

    if native_plat != target_plat or platform.machine() != machine:
        return machine

    try:
        import archspec.cpu

        return str(archspec.cpu.host())
    except ImportError:
        return machine


def calculate_channel_urls(
    channel_urls=(), prepend=True, platform=None, use_local=False
):
    if use_local:
        channel_urls = ["local"] + list(channel_urls)
    if prepend:
        channel_urls += context.channels

    subdirs = (platform, "noarch") if platform is not None else context.subdirs
    return all_channel_urls(channel_urls, subdirs=subdirs)


def get_reduced_index(prefix, channels, subdirs, specs, repodata_fn):
    records = IndexedSet()
    collected_names = set()
    collected_track_features = set()
    pending_names = set()
    pending_track_features = set()

    def push_spec(spec):
        name = spec.get_raw_value("name")
        if name and name not in collected_names:
            pending_names.add(name)
        track_features = spec.get_raw_value("track_features")
        if track_features:
            for ftr_name in track_features:
                if ftr_name not in collected_track_features:
                    pending_track_features.add(ftr_name)

    def push_record(record):
        try:
            combined_depends = record.combined_depends
        except InvalidSpec as e:
            log.warning(
                "Skipping %s due to InvalidSpec: %s",
                record.record_id(),
                e._kwargs["invalid_spec"],
            )
            return
        push_spec(MatchSpec(record.name))
        for _spec in combined_depends:
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
            new_records = SubdirData.query_all(
                spec, channels=channels, subdirs=subdirs, repodata_fn=repodata_fn
            )
            for record in new_records:
                push_record(record)
            records.update(new_records)

        while pending_track_features:
            feature_name = pending_track_features.pop()
            collected_track_features.add(feature_name)
            spec = MatchSpec(track_features=feature_name)
            new_records = SubdirData.query_all(
                spec, channels=channels, subdirs=subdirs, repodata_fn=repodata_fn
            )
            for record in new_records:
                push_record(record)
            records.update(new_records)

    reduced_index = {rec: rec for rec in records}

    if prefix is not None:
        _supplement_index_with_prefix(reduced_index, prefix)

    if context.offline or (
        "unknown" in context._argparse_args and context._argparse_args.unknown
    ):
        # This is really messed up right now.  Dates all the way back to
        # https://github.com/conda/conda/commit/f761f65a82b739562a0d997a2570e2b8a0bdc783
        # TODO: revisit this later
        _supplement_index_with_cache(reduced_index)

    # add feature records for the solver
    known_features = set()
    for rec in reduced_index.values():
        known_features.update((*rec.track_features, *rec.features))
    known_features.update(context.track_features)
    for ftr_str in known_features:
        rec = make_feature_record(ftr_str)
        reduced_index[rec] = rec

    _supplement_index_with_system(reduced_index)

    return reduced_index
