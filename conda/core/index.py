# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Tools for fetching the current index."""

from __future__ import annotations

from itertools import chain
from logging import getLogger
from typing import TYPE_CHECKING

from boltons.setutils import IndexedSet

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

if TYPE_CHECKING:
    from typing import Any


log = getLogger(__name__)


def check_allowlist(channel_urls: list[str]) -> None:
    """
    Check if the given channel URLs are allowed by the context's allowlist.

    :param channel_urls: A list of channel URLs to check against the allowlist.
    :raises ChannelNotAllowed: If any URL is not in the allowlist.
    """
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
    channel_urls: tuple[str] = (),
    prepend: bool = True,
    platform: str | None = None,
    use_local: bool = False,
    use_cache: bool = False,
    unknown: bool | None = None,
    prefix: str | None = None,
    repodata_fn: str = context.repodata_fns[-1],
) -> dict:
    """
    Return the index of packages available on the channels

    If prepend=False, only the channels passed in as arguments are used.
    If platform=None, then the current platform is used.
    If prefix is supplied, then the packages installed in that prefix are added.

    :param channel_urls: Channels to include in the index.
    :param prepend: If False, only the channels passed in are used.
    :param platform: Target platform for the index.
    :param use_local: Whether to use local channels.
    :param use_cache: Whether to use cached index information.
    :param unknown: Include unknown packages.
    :param prefix: Path to environment prefix to include in the index.
    :param repodata_fn: Filename of the repodata file.
    :return: A dictionary representing the package index.
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
    channel_urls: list[str],
    use_cache: bool = False,
    index: dict | None = None,
    repodata_fn: str = context.repodata_fns[-1],
) -> dict:
    """
    Fetch the package index from the specified channels.

    :param channel_urls: A list of channel URLs to fetch the index from.
    :param use_cache: Whether to use the cached index data.
    :param index: An optional pre-existing index to update.
    :param repodata_fn: The name of the repodata file.
    :return: A dictionary representing the fetched or updated package index.
    """
    log.debug("channel_urls=" + repr(channel_urls))
    index = {}
    with ThreadLimitedThreadPoolExecutor() as executor:
        subdir_instantiator = lambda url: SubdirData(
            Channel(url), repodata_fn=repodata_fn
        )
        for f in executor.map(subdir_instantiator, channel_urls):
            index.update((rec, rec) for rec in f.iter_records())
    return index


def dist_str_in_index(index: dict[Any, Any], dist_str: str) -> bool:
    """
    Check if a distribution string matches any package in the index.

    :param index: The package index.
    :param dist_str: The distribution string to match against the index.
    :return: True if there is a match; False otherwise.
    """
    match_spec = MatchSpec.from_dist_str(dist_str)
    return any(match_spec.match(prec) for prec in index.values())


def _supplement_index_with_prefix(index: dict[Any, Any], prefix: str) -> None:
    """
    Supplement the given index with information from the specified environment prefix.

    :param index: The package index to supplement.
    :param prefix: The path to the environment prefix.
    """
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


def _supplement_index_with_cache(index: dict[Any, Any]) -> None:
    """
    Supplement the given index with packages from the cache.

    :param index: The package index to supplement.
    """
    # supplement index with packages from the cache
    for pcrec in PackageCacheData.get_all_extracted_entries():
        if pcrec in index:
            # The downloaded repodata takes priority
            current_record = index[pcrec]
            index[pcrec] = PackageCacheRecord.from_objects(current_record, pcrec)
        else:
            index[pcrec] = pcrec


def _make_virtual_package(
    name: str, version: str | None = None, build_string: str | None = None
) -> PackageRecord:
    """
    Create a virtual package record.

    :param name: The name of the virtual package.
    :param version: The version of the virtual package, defaults to "0".
    :param build_string: The build string of the virtual package, defaults to "0".
    :return: A PackageRecord representing the virtual package.
    """
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


def _supplement_index_with_features(
    index: dict[PackageRecord, PackageRecord], features: list[str] = []
) -> None:
    """
    Supplement the given index with virtual feature records.

    :param index: The package index to supplement.
    :param features: A list of feature names to add to the index.
    """
    for feature in chain(context.track_features, features):
        rec = make_feature_record(feature)
        index[rec] = rec


def _supplement_index_with_system(index: dict[PackageRecord, PackageRecord]) -> None:
    """
    Loads and populates virtual package records from conda plugins
    and adds them to the provided index, unless there is a naming
    conflict.

    :param index: The package index to supplement.
    """
    for package in context.plugin_manager.get_virtual_packages():
        rec = _make_virtual_package(f"__{package.name}", package.version, package.build)
        index[rec] = rec


def get_archspec_name() -> str | None:
    """
    Determine the architecture specification name for the current environment.

    :return: The architecture name if available, otherwise None.
    """
    from ..base.context import _arch_names, non_x86_machines

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

    native_subdir = context._native_subdir()

    if native_subdir != context.subdir:
        return machine
    else:
        import archspec.cpu

        return str(archspec.cpu.host())


def calculate_channel_urls(
    channel_urls: tuple[str] = (),
    prepend: bool = True,
    platform: str | None = None,
    use_local: bool = False,
) -> list[str]:
    """
    Calculate the full list of channel URLs to use based on the given parameters.

    :param channel_urls: Initial list of channel URLs.
    :param prepend: Whether to prepend default channels to the list.
    :param platform: The target platform for the channels.
    :param use_local: Whether to include the local channel.
    :return: The calculated list of channel URLs.
    """
    if use_local:
        channel_urls = ["local"] + list(channel_urls)
    if prepend:
        channel_urls += context.channels

    subdirs = (platform, "noarch") if platform is not None else context.subdirs
    return all_channel_urls(channel_urls, subdirs=subdirs)


def get_reduced_index(
    prefix: str | None,
    channels: list[str],
    subdirs: list[str],
    specs: list[MatchSpec],
    repodata_fn: str,
) -> dict:
    """
    Generate a reduced package index based on the given specifications.

    This function is useful for optimizing the solver by reducing the amount
    of data it needs to consider.

    :param prefix: Path to an environment prefix to include installed packages.
    :param channels: A list of channel names to include in the index.
    :param subdirs: A list of subdirectories to consider for each channel.
    :param specs: A list of MatchSpec objects to filter the packages.
    :param repodata_fn: Filename of the repodata file to use.
    :return: A dictionary representing the reduced package index.
    """
    records = IndexedSet()
    collected_names = set()
    collected_track_features = set()
    pending_names = set()
    pending_track_features = set()

    def push_spec(spec: MatchSpec) -> None:
        """
        Add a package name or track feature from a MatchSpec to the pending set.

        :param spec: The MatchSpec to process.
        """
        name = spec.get_raw_value("name")
        if name and name not in collected_names:
            pending_names.add(name)
        track_features = spec.get_raw_value("track_features")
        if track_features:
            for ftr_name in track_features:
                if ftr_name not in collected_track_features:
                    pending_track_features.add(ftr_name)

    def push_record(record: PackageRecord) -> None:
        """
        Process a package record to collect its dependencies and features.

        :param record: The package record to process.
        """
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
