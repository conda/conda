# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Tools for fetching the current index."""

from __future__ import annotations

from collections import UserDict, deque
from collections.abc import Mapping
from logging import getLogger
from posixpath import normpath
from typing import TYPE_CHECKING
from urllib.parse import urlsplit, urlunsplit

from ..base.constants import REPODATA_FN
from ..base.context import context, validate_channels
from ..common.iterators import groupby_to_dict, unique
from ..exceptions import (
    ChannelError,
    CondaKeyError,
    InvalidSpec,
    PackagesNotFoundError,
)
from ..models.channel import Channel
from ..models.match_spec import MatchSpec
from ..models.records import EMPTY_LINK, PackageCacheRecord, PackageRecord, PrefixRecord
from .package_cache_data import PackageCacheData
from .prefix_data import PrefixData
from .subdir_data import SubdirData

if TYPE_CHECKING:
    from collections.abc import Iterable
    from typing import Any, Self

    from ..common.path import PathType
    from .exclude_newer import ExcludeNewerPolicy


log = getLogger(__name__)

LAST_CHANNEL_URLS = []


def _related_channel(channel: Channel, reference: object) -> Channel:
    if not isinstance(reference, str) or not reference.startswith("../"):
        raise ChannelError(
            f"Channel relation for {channel.base_url} must be a relative path starting with '../'."
        )
    parts = urlsplit(reference)
    if (
        parts.scheme
        or parts.netloc
        or parts.query
        or parts.fragment
        or "\\" in reference
    ):
        raise ChannelError(f"Invalid channel relation for {channel.base_url}.")
    origin = urlsplit(channel.base_url)
    path = normpath(f"{origin.path.rstrip('/')}/{parts.path}")
    related = Channel(urlunsplit(origin._replace(path=path)))
    # A path token belongs to the declaring channel. Resolve the target's token
    # through normal channel configuration instead of forwarding that token.
    target = urlsplit(related.base_url)
    if (
        channel.auth
        and not related.auth
        and (origin.scheme, origin.netloc) == (target.scheme, target.netloc)
    ):
        related = Channel(**{**related.dump(), "auth": channel.auth})
    return related


def resolve_channels(
    channels: Iterable[Channel | str],
    subdirs: Iterable[str] | None = None,
    *,
    repodata_fn: str = REPODATA_FN,
    max_depth: int | None = None,
    use_shards: bool | None = None,
) -> tuple[Channel, ...]:
    """Return channels in priority order after discovering their CEP 42 relations.

    Expand multichannels into individual channels and preserve explicit head
    ordering. Callers should keep the original heads when recording environment
    configuration or lockfiles. A maximum depth of zero disables discovery.

    All metadata is obtained through conda's normal repodata and shard fetchers.
    Related channels are checked against channel policy before metadata is read.
    Explicit ``subdirs`` override any platform in the input channels, matching
    :meth:`Channel.urls`. ``noarch`` is always included during discovery.
    """
    from .._private.shards.shards import fetch_shards_index

    max_depth = context.channel_relations_max_depth if max_depth is None else max_depth
    if max_depth < 0:
        raise ChannelError("channel_relations_max_depth must be non-negative.")
    use_shards = context.repodata_use_shards if use_shards is None else use_shards
    heads = {}
    for value in channels:
        for channel in Channel(value).channels:
            if channel.base_url is not None:
                heads.setdefault(channel.base_url, channel)
    validate_channels(tuple(heads.values()))
    if not max_depth or not heads:
        return tuple(heads.values())

    if subdirs is None:
        subdirs = tuple(
            dict.fromkeys(
                subdir
                for channel in heads.values()
                for subdir in ((channel.subdir,) if channel.subdir else context.subdirs)
            )
        )
    subdirs = tuple(dict.fromkeys((*subdirs, "noarch")))
    nodes = dict(heads)
    head_order = {url: i for i, url in enumerate(heads)}
    successors = {url: [] for url in heads}
    for before, after in zip(heads, tuple(heads)[1:]):
        successors[before].append(after)

    pending = deque((url, 0) for url in heads)
    while pending:
        url, depth = pending.popleft()
        channel = nodes[url]
        for subdir in subdirs:
            source = SubdirData(
                Channel(**{**channel.dump(), "platform": subdir}),
                repodata_fn=repodata_fn,
            )
            if use_shards and (shards := fetch_shards_index(source)) is not None:
                relations = shards.repodata_no_packages.get("info", {}).get(
                    "channel_relations", {}
                )
            else:
                relations = source.channel_relations
            if not isinstance(relations, Mapping):
                raise ChannelError(f"Channel relations for {url} must be a mapping.")
            targets = {
                key: _related_channel(channel, relations[key])
                for key in ("base", "overrides")
                if key in relations
            }
            if (
                "base" in targets
                and "overrides" in targets
                and targets["base"].base_url == targets["overrides"].base_url
            ):
                raise ChannelError(
                    f"Channel {url} declares the same base and overrides."
                )
            for key, target in targets.items():
                target_url = target.base_url
                if target_url not in nodes:
                    if depth >= max_depth:
                        raise ChannelError(
                            f"Channel relation depth exceeds {max_depth} at {url}."
                        )
                    validate_channels((target,))
                    nodes[target_url] = target
                    successors[target_url] = []
                    pending.append((target_url, depth + 1))
                before, after = (
                    (target_url, url) if key == "base" else (url, target_url)
                )
                if (
                    before in head_order
                    and after in head_order
                    and head_order[before] > head_order[after]
                ):
                    continue
                if after not in successors[before]:
                    successors[before].append(after)

    resolved = []
    visited = set()
    active = set()
    # Visit heads in reverse priority order so unrelated heads do not separate
    # channels connected by relations when several topological orders are valid.
    for root in (*reversed(heads), *reversed(nodes)):
        if root in visited:
            continue
        active.add(root)
        pending_nodes = [(root, iter(successors[root]))]
        while pending_nodes:
            url, following = pending_nodes[-1]
            after = next(following, None)
            if after is None:
                pending_nodes.pop()
                active.remove(url)
                visited.add(url)
                resolved.append(nodes[url])
            elif after in active:
                raise ChannelError(
                    f"Channel relations contain a cycle involving {after}."
                )
            elif after not in visited:
                active.add(after)
                pending_nodes.append((after, iter(successors[after])))
    return tuple(reversed(resolved))


class Index(UserDict):
    """The ``Index`` provides information about available packages from all relevant sources.

    There are four types of sources for package information, namely

    Channels
        represent packages available from standard sources identified with a url, mostly online,
        but can also be on a local filesystem using the ``file://`` scheme.
        Programatically, channels are represented by :class:`conda.models.channel.Channel`, their data
        is fetched using :class:`conda.core.subdir_data.SubdirData`.

        For more information see :ref:`concepts-channels`.

        Individual packages from channels are usually represented by :class:`conda.models.records.PackageRecord`.

    Prefix
        represents packages that are already installed. Every :class:`Index` can be associated
        with exactly one Prefix, which is the location of one of the conda :ref:`concepts-conda-environments`.
        The package information about the installed packages is represented by :class:`conda.core.prefix_data.PrefixData`.

        Individual packages from prefixes are usually represented by :class:`conda.models.records.PrefixRecord`.

    Package Cache
        represents packages that are locally unpacked, but may not be installed in the environment
        associated with this index. These are usually packages that have been installed in any environment
        of the local conda installation, but may have been removed from all environments by now.

        Individual packages from the package are usually represented by :class:`conda.models.records.PackageCacheRecord`.

    Virtual Packages
        represent properties of the system, not actual conda packages in the normal sense. These are,
        for example, system packages that inform the solver about the operating system in use, or
        track features that can be used to steer package priority.

        Individual virtual packages are represented by special :class:`conda.models.records.PackageRecord`,
        see :meth:`conda.models.records.PackageRecord.virtual_package` and
        :meth:`conda.models.records.PackageRecord.feature`.
    """

    def __init__(
        self,
        channels: Iterable[str | Channel] = (),
        prepend: bool = True,
        platform: str | None = None,
        subdirs: tuple[str, ...] | None = None,
        use_local: bool = False,
        use_cache: bool | None = None,
        prefix: PathType | PrefixData | None = None,
        repodata_fn: str | None = context.repodata_fns[-1],
        use_system: bool = False,
        exclude_newer_policy: ExcludeNewerPolicy | None = None,
    ) -> None:
        """Initializes a new index with the desired components.

        Args:
          channels: channels identified by canonical names or URLS or Channel objects;
            for more details, see :meth:`conda.models.channel.Channel.from_value`
          prepend: if ``True`` (default), add configured channel with higher priority than passed channels;
            if ``False``, do *not* add configured channels.
          platform: see ``subdirs``.
          subdirs: platform and subdirs determine the selection of subdirs in the channels;
            if both are ``None``, subdirs is taken from the configuration;
            if both are given, ``subdirs`` takes precedence and ``platform`` is ignored;
            if only ``platform`` is given, subdirs will be ``(platform, "noarch")``;
            if ``subdirs`` is given, subdirs will be ``subdirs``.
          use_local: if ``True``, add the special "local" channel for locally built packages with lowest priority.
          use_cache: if ``True``, add packages from the package cache.
          prefix: associate prefix with this index and add its packages.
          repodata_fn: filename of the repodata, default taken from config, almost always "repodata.json".
          use_system: if ``True``, add system packages, that is virtual packages defined by plugins, usually used
            to make intrinsic information about the system, such as cpu architecture or operating system, available
            to the solver.
        """
        channels = list(channels)
        if use_local:
            channels = ["local", *channels]
        if prepend:
            channels += context.channels
        self._channels = tuple(unique(channels))
        if subdirs:
            if platform:
                log.warning("subdirs is %s, ignoring platform %s", subdirs, platform)
        else:
            subdirs = (platform, "noarch") if platform is not None else context.subdirs
        self._subdirs = subdirs
        self._repodata_fn = repodata_fn
        self._channel_relations_loaded = False
        self._set_channels(self._channels)
        if prefix is None:
            self.prefix_data = None
        elif isinstance(prefix, PrefixData):
            self.prefix_data = prefix
        else:
            self.prefix_data = PrefixData(prefix)
        self.use_cache = True if use_cache is None and context.offline else use_cache
        self.use_system = use_system
        from .exclude_newer import ExcludeNewerPolicy

        self.exclude_newer_policy = exclude_newer_policy or ExcludeNewerPolicy()

    def _set_channels(self, channels: Iterable[str | Channel]) -> None:
        self.channels: dict[str | Channel, list[SubdirData]] = {}
        expanded_channels = {}
        head_labels = {
            Channel(value).base_url: value for value in reversed(self._channels)
        }
        for channel in channels:
            channel_key = head_labels.get(Channel(channel).base_url, str(channel))
            self.channels[channel_key] = []
            for url in Channel(channel).urls(True, self._subdirs):
                url_as_channel = Channel(url)
                self.channels[channel_key].append(
                    SubdirData(url_as_channel, repodata_fn=self._repodata_fn)
                )
                expanded_channels.setdefault(url_as_channel, None)
        self.expanded_channels: tuple[Channel, ...] = tuple(expanded_channels)
        # LAST_CHANNEL_URLS is still used in conda-build and must be maintained for the moment.
        LAST_CHANNEL_URLS.clear()
        LAST_CHANNEL_URLS.extend(self.expanded_channels)

    def _load_channel_relations(self) -> None:
        if not self._channel_relations_loaded:
            channels = resolve_channels(
                self._channels,
                self._subdirs,
                repodata_fn=self._repodata_fn,
                use_shards=False,
            )
            head_urls = tuple(
                dict.fromkeys(
                    channel.base_url
                    for head in self._channels
                    for channel in Channel(head).channels
                )
            )
            if tuple(channel.base_url for channel in channels) != head_urls:
                self._set_channels(channels)
            self._channel_relations_loaded = True

    @property
    def cache_entries(self) -> tuple[PackageCacheRecord, ...]:
        """Contents of the package cache if active.

        Returns:
          All packages available from the package cache.
        """
        try:
            return self._cache_entries
        except AttributeError:
            self.reload(cache=True)
        return self._cache_entries

    @property
    def system_packages(self) -> dict[PackageRecord, PackageRecord]:
        """System packages provided by plugins.

        Returns:
          Identity mapping of the available system packages in a ``dict``.
        """
        try:
            return self._system_packages
        except AttributeError:
            self.reload(system=True)
        return self._system_packages

    @property
    def features(self) -> dict[PackageRecord, PackageRecord]:
        """Active tracking features.

        Returns:
          Identity mapping of the local tracking features in a ``dict``.
        """
        try:
            return self._features
        except AttributeError:
            self.reload(features=True)
        return self._features

    def reload(
        self,
        *,
        prefix: bool = False,
        cache: bool = False,
        features: bool = False,
        system: bool = False,
    ) -> None:
        """Reload one or more of the index components.

        Can be used to refresh the index with new information, for example after a new
        package has been installed into the index.

        Args:
          prefix: if ``True``, reload the prefix data.
          cache: if ``True``, reload the package cache.
          features: if ``True``, reload the tracking features.
          system: if ``True``, reload the system packages.
        """
        has_data = hasattr(self, "_data")
        if prefix:
            if self.prefix_data:
                self.prefix_data.reload()
            if has_data:
                self._supplement_index_dict_with_prefix()
        if cache:
            self._cache_entries = PackageCacheData.get_all_extracted_entries()
            if has_data:
                self._supplement_index_dict_with_cache()
        if features:
            self._features = {
                (rec := PackageRecord.feature(track_feature)): rec
                for track_feature in context.track_features
            }
            if has_data:
                self._data.update(self.features)
        if system:
            self._system_packages = {
                package: package
                for package in context.plugin_manager.get_virtual_package_records()
            }
            if has_data:
                self._data.update(self.system_packages)

    def __repr__(self) -> str:
        channels = ", ".join(self.channels.keys())
        return f"<{self.__class__.__name__}(channels=[{channels}])>"

    def get_reduced_index(self, specs: Iterable[MatchSpec]) -> ReducedIndex:
        """Create a reduced index with a subset of packages.

        Can be used to create a reduced index as a subset from an existing index.

        Args:
          specs: the specs that span the subset.

        Returns:
          a reduced index with the same sources as this index, but limited to ``specs``
          and their dependency graph.
        """
        return ReducedIndex(
            specs=specs,
            channels=self._channels,
            prepend=False,
            subdirs=self._subdirs,
            use_local=False,
            use_cache=self.use_cache,
            prefix=self.prefix_data,
            repodata_fn=self._repodata_fn,
            use_system=self.use_system,
            exclude_newer_policy=(
                self.exclude_newer_policy
                if self.exclude_newer_policy.active
                else context.exclude_newer_policy
            ),
        )

    @property
    def data(self) -> dict[PackageRecord, PackageRecord]:
        """The entire index as a dict; avoid if possible.

        Warning:
          This returns the entire contents of the index as a single identity mapping in
          a ``dict``. This may be convenient, but it comes at a cost because all sources
          must be fully loaded at significant overhead for :class:`~conda.models.records.PackageRecord`
          construction for **every** package.

          Hence, all uses of :attr:`data`, including all iteration over the entire index,
          is strongly discouraged.
        """
        try:
            return self._data
        except AttributeError:
            self._realize()
            return self._data

    @data.setter
    def data(self, value: dict[PackageRecord, PackageRecord]) -> None:
        self._data = value

    def _supplement_index_dict_with_prefix(self) -> None:
        """
        Supplement the index with information from its prefix.
        """
        if self.prefix_data is None:
            return

        # supplement index with information from prefix/conda-meta
        for prefix_record in self.prefix_data.iter_records():
            if prefix_record in self._data:
                current_record = self._data[prefix_record]
                # The downloaded repodata takes priority, so we do not overwrite.
                # We do, however, copy the link information so that the solver (i.e. resolve)
                # knows this package is installed.
                link = prefix_record.get("link") or EMPTY_LINK
                self._data[prefix_record] = PrefixRecord.from_objects(
                    current_record, prefix_record, link=link
                )
            else:
                # If the package is not in the repodata, use the local data.
                # If the channel is known but the package is not in the index, it
                # is because 1) the channel is unavailable offline, or 2) it no
                # longer contains this package. Either way, we should prefer any
                # other version of the package to this one. On the other hand, if
                # it is in a channel we don't know about, assign it a value just
                # above the priority of all known channels.
                self._data[prefix_record] = prefix_record

    def _supplement_index_dict_with_cache(self) -> None:
        # supplement index with packages from the cache
        for pcrec in self.cache_entries:
            if pcrec in self._data:
                # The downloaded repodata takes priority
                current_record = self._data[pcrec]
                self._data[pcrec] = PackageCacheRecord.from_objects(
                    current_record, pcrec
                )
            else:
                self._data[pcrec] = pcrec

    def _realize(self) -> None:
        self._load_channel_relations()
        self._data = {}
        for subdir_datas in self.channels.values():
            for subdir_data in subdir_datas:
                self._data.update((prec, prec) for prec in subdir_data.iter_records())
        self._supplement_index_dict_with_prefix()
        if self.use_cache:
            self._supplement_index_dict_with_cache()
        self._data.update(self.features)
        if self.use_system:
            self._data.update(self.system_packages)

    def _retrieve_from_channels(self, key: PackageRecord) -> PackageRecord | None:
        self._load_channel_relations()
        for subdir_datas in reversed(self.channels.values()):
            for subdir_data in subdir_datas:
                if key.subdir != subdir_data.channel.subdir:
                    continue
                prec_candidates = list(subdir_data.query(key))
                if not prec_candidates:
                    continue
                if len(prec_candidates) > 1:
                    raise CondaKeyError(
                        key, "More than one matching package found in channels."
                    )
                prec = prec_candidates[0]
                if prec:
                    return prec
        return None

    def _retrieve_all_from_channels(self, key: PackageRecord) -> list[PackageRecord]:
        self._load_channel_relations()
        precs = []
        for subdir_datas in reversed(self.channels.values()):
            for subdir_data in subdir_datas:
                if hasattr(key, "subdir") and key.subdir != subdir_data.channel.subdir:
                    continue
                precs.extend(subdir_data.query(key))
        if self.exclude_newer_policy.active:
            return list(self.exclude_newer_policy.filter_records(precs))
        return precs

    def _update_from_prefix(
        self, key: PackageRecord, prec: PackageRecord | None
    ) -> PackageRecord | None:
        prefix_prec = self.prefix_data.get(key.name, None) if self.prefix_data else None
        if prefix_prec and prefix_prec == prec:
            if prec:
                link = prefix_prec.get("link") or EMPTY_LINK
                prec = PrefixRecord.from_objects(prec, prefix_prec, link=link)
            else:
                prec = prefix_prec
        return prec

    def _update_from_cache(
        self, key: PackageRecord, prec: PackageRecord | None
    ) -> PackageRecord | None:
        for pcrec in self.cache_entries:
            if pcrec == key:
                if prec:
                    # The downloaded repodata takes priority
                    return PackageCacheRecord.from_objects(prec, pcrec)
                else:
                    return pcrec
        return prec

    def __getitem__(self, key: PackageRecord) -> PackageRecord:
        if not isinstance(key, PackageRecord):
            raise TypeError(
                "Can only retrieve PackageRecord objects. Got {}.", type(key)
            )
        try:
            return self._data[key]
        except AttributeError:
            pass
        if key.name.startswith("__"):
            try:
                return self.system_packages[key]
            except KeyError:
                pass
        if key.name.endswith("@"):
            try:
                return self.features[key]
            except KeyError:
                pass
        prec = self._retrieve_from_channels(key)
        prec = self._update_from_prefix(key, prec)
        if self.use_cache:
            prec = self._update_from_cache(key, prec)
        if prec is None:
            raise KeyError((key,))
        return prec

    def __contains__(self, key: PackageRecord) -> bool:
        try:
            _ = self[key]
            return True
        except (PackagesNotFoundError, KeyError):
            return False

    def __copy__(self) -> Self:
        inst = self.__class__.__new__(self.__class__)
        inst.__dict__.update(self.__dict__)
        if "_data" in self.__dict__:
            inst.__dict__["_data"] = self.__dict__["_data"].copy()
        return inst

    def copy(self) -> Self:
        """Lazy shallow copy that does not realize unrealized package records.

        Overrides ``UserDict.copy``, which reads ``self.data`` and calls
        ``update`` and therefore forces
        ``Index._realize()`` — constructing a PackageRecord for every package
        of every channel — even though ``__copy__`` preserves unrealized
        state. See conda/conda-build#4961.
        """
        return self.__copy__()


class ReducedIndex(Index):
    """Index that contains a subset of available packages.

    Like :class:`Index`, this makes information about packages from the same four
    sources available. However, the contents of the reduced index is limited to
    a subset of packages relevant to a given specification.
    This works by taking into account all packages that match the given specification
    together with their dependencies and their dependencies dependencies, etc.

    Note:
        See :meth:`Index.get_reduced_index` for convenient construction.
    """

    def __init__(
        self,
        specs: Iterable[MatchSpec],
        channels: tuple[str, ...] = (),
        prepend: bool = True,
        platform: str | None = None,
        subdirs: tuple[str, ...] | None = None,
        use_local: bool = False,
        use_cache: bool | None = None,
        prefix: PathType | PrefixData | None = None,
        repodata_fn: str | None = context.repodata_fns[-1],
        use_system: bool = False,
        exclude_newer_policy: ExcludeNewerPolicy | None = None,
    ) -> None:
        """Initialize a new reduced index.

        Args:
          specs: the collection of specifications that span the subset of packages.
          all other args: see :class:`Index`.
        """
        super().__init__(
            channels,
            prepend,
            platform,
            subdirs,
            use_local,
            use_cache,
            prefix,
            repodata_fn,
            use_system,
            exclude_newer_policy or context.exclude_newer_policy,
        )
        self.specs = specs
        self._derive_reduced_index()

    def __repr__(self) -> str:
        channels = ", ".join(self.channels.keys())
        return f"<{self.__class__.__name__}(spec={self.specs}, channels=[{channels}])>"

    def _derive_reduced_index(self) -> None:
        records = {}
        collected_names = set()
        collected_track_features = set()
        pending_names = set()
        pending_track_features = set()
        cache_records = (
            groupby_to_dict(lambda record: record.name, self.cache_entries)
            if self.use_cache
            else {}
        )

        def push_specs(*specs: MatchSpec | str) -> None:
            """
            Add a package name or track feature from a MatchSpec to the pending set.

            Args:
                *specs: The MatchSpecs to process.
            """
            for spec in map(MatchSpec, specs):
                name = spec.get_raw_value("name")
                if name and name not in collected_names:
                    pending_names.add(name)
                track_features = spec.get_raw_value("track_features")
                if track_features:
                    for ftr_name in track_features:
                        if ftr_name not in collected_track_features:
                            pending_track_features.add(ftr_name)

        def push_records(*records: PackageRecord) -> None:
            """
            Process package records to collect their dependencies and features.

            Args:
                *records: The package records to process.
            """
            for record in records:
                try:
                    combined_depends = record.combined_depends
                except InvalidSpec as e:
                    log.warning(
                        "Skipping %s due to InvalidSpec: %s",
                        record.record_id(),
                        e._kwargs["invalid_spec"],
                    )
                    return
                push_specs(
                    record.name,
                    *combined_depends,
                    *(
                        MatchSpec(track_features=ftr_name)
                        for ftr_name in record.track_features
                    ),
                )

        if self.prefix_data:
            push_records(*self.prefix_data.iter_records())
        push_specs(*self.specs)

        while pending_names or pending_track_features:
            while pending_names:
                name = pending_names.pop()
                collected_names.add(name)
                spec = MatchSpec(name)
                # new_records = SubdirData.query_all(
                #     spec, channels=channels, subdirs=subdirs, repodata_fn=repodata_fn
                # )
                new_records = dict.fromkeys(self._retrieve_all_from_channels(spec))
                for record in new_records:
                    push_records(record)
                for record in cache_records.get(name, ()):
                    if record not in new_records:
                        push_records(record)
                records.update(new_records)

            while pending_track_features:
                feature_name = pending_track_features.pop()
                collected_track_features.add(feature_name)
                spec = MatchSpec(track_features=feature_name)
                # new_records = SubdirData.query_all(
                #     spec, channels=channels, subdirs=subdirs, repodata_fn=repodata_fn
                # )
                new_records = dict.fromkeys(self._retrieve_all_from_channels(spec))
                for record in new_records:
                    push_records(record)
                for records_for_name in cache_records.values():
                    for record in records_for_name:
                        if record not in new_records and spec.match(record):
                            push_records(record)
                records.update(new_records)

        self._data = {rec: rec for rec in records}

        self._supplement_index_dict_with_prefix()

        if self.use_cache:
            self._supplement_index_dict_with_cache()

        # add feature records for the solver
        known_features = set()
        for rec in self._data.values():
            known_features.update((*rec.track_features, *rec.features))
        known_features.update(context.track_features)
        for known_feature in known_features:
            rec = PackageRecord.feature(known_feature)
            self._data[rec] = rec

        self._data.update(self.system_packages)


def dist_str_in_index(index: dict[Any, Any], dist_str: str) -> bool:
    """
    Check if a distribution string matches any package in the index.

    Args:
        index: The package index.
        dist_str: The distribution string to match against the index.

    Returns:
        True if there is a match; False otherwise.
    """
    match_spec = MatchSpec.from_dist_str(dist_str)
    return any(match_spec.match(prec) for prec in index.values())


def get_archspec_name() -> str | None:
    """
    Determine the architecture specification name for the current environment.

    Returns:
        The architecture name if available, otherwise None.
    """
    from ..base.context import _arch_names, non_x86_machines

    target_plat, target_arch = context.subdir.split("-")
    # This has to reverse what Context.subdir is doing
    if target_arch in non_x86_machines:
        machine = target_arch
    elif target_arch == "zos":
        return None
    elif target_arch.isdigit():
        machine = _arch_names[target_arch]
    else:
        return None

    native_subdir = context._native_subdir()

    if native_subdir != context.subdir:
        return machine
    else:
        import archspec.cpu

        return str(archspec.cpu.host())
