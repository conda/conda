# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Tools for fetching the current index."""

from __future__ import annotations

from collections import UserDict
from itertools import chain
from logging import getLogger
from pathlib import Path
from typing import TYPE_CHECKING

from boltons.setutils import IndexedSet

from ..base.context import context
from ..common.io import ThreadLimitedThreadPoolExecutor, time_recorder
from ..deprecations import deprecated
from ..exceptions import (
    ChannelNotAllowed,
    InvalidSpec,
    OperationNotAllowed,
    PackagesNotFoundError,
)
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


class Index(UserDict):
    def __init__(
        self,
        channels=(),
        prepend=True,
        platform=None,
        subdirs=None,
        use_local=False,
        unknown=None,
        prefix=None,
        repodata_fn=context.repodata_fns[-1],
        add_system=False,
    ) -> None:
        if use_local:
            channels = ["local"] + list(channels)
        if prepend:
            channels += context.channels
        self._channels = channels
        if subdirs:
            if platform:
                log.warning("subdirs is %s, ignoring platform %s", subdirs, platform)
        else:
            subdirs = (platform, "noarch") if platform is not None else context.subdirs
        self._subdirs = subdirs
        self._repodata_fn = repodata_fn
        self.channels = {}
        self.expanded_channels = []
        for channel in channels:
            urls = Channel(channel).urls(True, subdirs)
            check_allowlist(urls)
            expanded_channels = [Channel(url) for url in urls]
            self.channels[channel] = [
                SubdirData(expanded_channel, repodata_fn=repodata_fn)
                for expanded_channel in expanded_channels
            ]
            self.expanded_channels.extend(expanded_channels)
        LAST_CHANNEL_URLS.clear()
        LAST_CHANNEL_URLS.extend(self.expanded_channels)
        if prefix is None:
            self.prefix_path = None
        elif isinstance(prefix, PrefixData):
            self.prefix_path = prefix.prefix_path
        else:
            self.prefix_path = prefix
        self._prefix_data = None
        self.unknown = True if unknown is None and context.offline else unknown
        self.track_features = context.track_features
        self.add_system = add_system
        self.system_packages = {
            (
                rec := _make_virtual_package(
                    f"__{package.name}", package.version, package.build
                )
            ): rec
            for package in context.plugin_manager.get_virtual_packages()
        }

    @property
    def prefix_data(self):
        if self._prefix_data is None and self.prefix_path:
            self._prefix_data = PrefixData(self.prefix_path)
        return self._prefix_data

    def reload(self, prefix=False):
        if prefix:
            if self.prefix_data:
                self.prefix_data.reload()

    def __repr__(self):
        channels = ", ".join(self.channels.keys())
        return f"Index(channels=[{channels}])"

    def get_reduced_index(self, specs):
        return ReducedIndex(
            specs=specs,
            channels=self._channels,
            prepend=False,
            subdirs=self._subdirs,
            use_local=False,
            unknown=self.unknown,
            prefix=self.prefix_path,
            repodata_fn=self._repodata_fn,
            add_system=self.add_system,
        )

    @property
    def data(self):
        try:
            return self._data
        except AttributeError:
            self._realize()
            return self._data

    @data.setter
    def data(self, value):
        self._data = value

    def _supplement_index_dict_with_prefix(self, index_dict):
        """
        Supplement the index with information from its prefix.
        """
        # supplement index with information from prefix/conda-meta
        for prefix_record in self.prefix_data.iter_records():
            if prefix_record in index_dict:
                current_record = index_dict[prefix_record]
                if current_record.channel == prefix_record.channel:
                    # The downloaded repodata takes priority, so we do not overwrite.
                    # We do, however, copy the link information so that the solver (i.e. resolve)
                    # knows this package is installed.
                    link = prefix_record.get("link") or EMPTY_LINK
                    index_dict[prefix_record] = PrefixRecord.from_objects(
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
                    index_dict[prefix_record] = prefix_record
            else:
                # If the package is not in the repodata, use the local data.
                # If the channel is known but the package is not in the index, it
                # is because 1) the channel is unavailable offline, or 2) it no
                # longer contains this package. Either way, we should prefer any
                # other version of the package to this one. On the other hand, if
                # it is in a channel we don't know about, assign it a value just
                # above the priority of all known channels.
                index_dict[prefix_record] = prefix_record

    def _realize(self):
        _data = {}
        for subdir_datas in self.channels.values():
            for subdir_data in subdir_datas:
                _data.update((prec, prec) for prec in subdir_data.iter_records())
        if self.prefix_data:
            self._supplement_index_dict_with_prefix(_data)
        if self.unknown:
            _supplement_index_with_cache(_data)
        if self.track_features:
            _supplement_index_with_features(_data)
        if self.add_system:
            _data.update(self.system_packages)
        self._data = _data

    def _retrieve_from_channels(self, key):
        for subdir_datas in reversed(self.channels.values()):
            for subdir_data in subdir_datas:
                if key.subdir != subdir_data.channel.subdir:
                    continue
                prec_candidates = list(subdir_data.query(key))
                if not prec_candidates:
                    continue
                assert len(prec_candidates) == 1
                prec = prec_candidates[0]
                if prec:
                    return prec
        return None

    def _retrieve_all_from_channels(self, key):
        precs = []
        for subdir_datas in reversed(self.channels.values()):
            for subdir_data in subdir_datas:
                if hasattr(key, "subdir") and key.subdir != subdir_data.channel.subdir:
                    continue
                prec_candidates = list(subdir_data.query(key))
                if not prec_candidates:
                    continue
                precs.extend(prec_candidates)
        return precs

    def _update_from_prefix(self, key, prec):
        prefix_prec = self.prefix_data.get(key.name, None) if self.prefix_data else None
        if prefix_prec:
            if prec:
                if prec.channel == prefix_prec.channel:
                    link = prefix_prec.get("link") or EMPTY_LINK
                    prec = PrefixRecord.from_objects(prec, prefix_prec, link=link)
                else:
                    prefix_channel = prefix_prec.channel
                    prefix_channel._Channel__canonical_name = prefix_channel.url()
                    del prefix_prec._PackageRecord__pkey
                    prec = prefix_prec
            else:
                prec = prefix_prec
        return prec

    def _update_from_cache(self, key, prec):
        for pcrec in PackageCacheData.get_all_extracted_entries():
            if pcrec == key:
                if prec:
                    # The downloaded repodata takes priority
                    return PackageCacheRecord.from_objects(prec, pcrec)
                else:
                    return pcrec
        return prec

    def __getitem__(self, key):
        assert isinstance(key, PackageRecord)
        try:
            return self._data[key]
        except AttributeError:
            pass
        try:
            return self.system_packages[key]
        except KeyError:
            pass
        if self.track_features and key.name.endswith("@"):
            for feature in self.track_features:
                if feature == key.name[:-1]:
                    return make_feature_record(feature)
        prec = self._retrieve_from_channels(key)
        prec = self._update_from_prefix(key, prec)
        if self.unknown:
            prec = self._update_from_cache(key, prec)
        if prec is None:
            raise KeyError((key,))
        return prec

    def __contains__(self, key):
        try:
            _ = self[key]
            return True
        except (PackagesNotFoundError, KeyError):
            return False

    def __copy__(self):
        inst = self.__class__.__new__(self.__class__)
        inst.__dict__.update(self.__dict__)
        if "_data" in self.__dict__:
            inst.__dict__["_data"] = self.__dict__["_data"].copy()
        return inst


class ReducedIndex(Index):
    def __init__(
        self,
        specs,
        channels=(),
        prepend=True,
        platform=None,
        subdirs=None,
        use_local=False,
        unknown=None,
        prefix=None,
        repodata_fn=context.repodata_fns[-1],
        add_system=False,
    ) -> None:
        super().__init__(
            channels,
            prepend,
            platform,
            subdirs,
            use_local,
            unknown,
            prefix,
            repodata_fn,
            add_system,
        )
        self.specs = specs
        self._derive_reduced_index()

    def __repr__(self):
        channels = ", ".join(self.channels.keys())
        return f"ReducedIndex(spec={self.specs}, channels=[{channels}])"

    def _derive_reduced_index(self):
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

        # TODO: Should we really add the whole prefix?
        # if self.prefix:
        #     for prefix_rec in self.prefix.iter_records():
        #         push_record(prefix_rec)
        for spec in self.specs:
            push_spec(spec)

        while pending_names or pending_track_features:
            while pending_names:
                name = pending_names.pop()
                collected_names.add(name)
                spec = MatchSpec(name)
                # new_records = SubdirData.query_all(
                #     spec, channels=channels, subdirs=subdirs, repodata_fn=repodata_fn
                # )
                new_records = self._retrieve_all_from_channels(spec)
                for record in new_records:
                    push_record(record)
                records.update(new_records)

            while pending_track_features:
                feature_name = pending_track_features.pop()
                collected_track_features.add(feature_name)
                spec = MatchSpec(track_features=feature_name)
                # new_records = SubdirData.query_all(
                #     spec, channels=channels, subdirs=subdirs, repodata_fn=repodata_fn
                # )
                new_records = self._retrieve_all_from_channels(spec)
                for record in new_records:
                    push_record(record)
                records.update(new_records)

        self._data = {rec: rec for rec in records}

        if self.prefix_data:
            self._supplement_index_dict_with_prefix(self._data)

        # add feature records for the solver
        known_features = set()
        for rec in self._data.values():
            known_features.update((*rec.track_features, *rec.features))
        known_features.update(context.track_features)
        for ftr_str in known_features:
            rec = make_feature_record(ftr_str)
            self._data[rec] = rec

        self._data.update(
            {
                (
                    rec := _make_virtual_package(
                        f"__{package.name}", package.version, package.build
                    )
                ): rec
                for package in context.plugin_manager.get_virtual_packages()
            }
        )

        # _supplement_index_with_system(reduced_index)

        # if prefix is not None:
        #     _supplement_index_with_prefix(reduced_index, prefix)

        # if context.offline or (
        #     "unknown" in context._argparse_args and context._argparse_args.unknown
        # ):
        #     # This is really messed up right now.  Dates all the way back to
        #     # https://github.com/conda/conda/commit/f761f65a82b739562a0d997a2570e2b8a0bdc783
        #     # TODO: revisit this later
        #     _supplement_index_with_cache(reduced_index)

        # # add feature records for the solver
        # known_features = set()
        # for rec in reduced_index.values():
        #     known_features.update((*rec.track_features, *rec.features))
        # known_features.update(context.track_features)
        # for ftr_str in known_features:
        #     rec = make_feature_record(ftr_str)
        #     reduced_index[rec] = rec

        # _supplement_index_with_system(reduced_index)


LAST_CHANNEL_URLS = []


@time_recorder("get_index")
@deprecated("24.9", "25.3", addendum="Use `conda.core.Index` instead.")
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
    return Index(
        channel_urls,
        prepend,
        platform,
        None,
        use_local,
        unknown,
        prefix,
        repodata_fn,
    )


@deprecated("24.9", "25.3", addendum="Use `conda.core.Index` instead.")
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


@deprecated("24.9", "25.3", addendum="Use `conda.core.Index.reload` instead.")
def _supplement_index_with_prefix(
    index: Index | dict[Any, Any],
    prefix: str | PrefixData,
) -> None:
    """
    Supplement the given index with information from the specified environment prefix.

    :param index: The package index to supplement.
    :param prefix: The path to the environment prefix.
    """
    # supplement index with information from prefix/conda-meta
    if isinstance(prefix, PrefixData):
        prefix_data = Path(prefix)
        prefix_path = prefix.prefix_path
    else:
        prefix_path = Path(prefix)
        prefix_data = PrefixData(prefix)
    if isinstance(index, Index):
        if not prefix_path.samefile(Path(index.prefix_path)):
            raise OperationNotAllowed(
                "An index can only be supplemented with its own prefix."
            )
        index.reload(prefix=True)
        return

    for prefix_record in prefix_data.iter_records():
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
    if isinstance(index, Index):
        return
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

    return ReducedIndex(
        specs,
        channels=channels,
        prepend=False,
        subdirs=subdirs,
        use_local=False,
        unknown=False,
        prefix=prefix,
        repodata_fn=repodata_fn,
        add_system=True,
    )

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
