# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Tools for managing a subdir's repodata.json."""

from __future__ import annotations

import pickle
from collections import UserList, defaultdict
from functools import partial
from itertools import chain
from logging import getLogger
from os.path import exists, getmtime, isfile, join, splitext
from pathlib import Path
from time import time
from typing import TYPE_CHECKING

from boltons.setutils import IndexedSet

from ..auxlib.ish import dals
from ..base.constants import CONDA_PACKAGE_EXTENSION_V1, REPODATA_FN
from ..base.context import context
from ..common.io import DummyExecutor, ThreadLimitedThreadPoolExecutor, dashlist
from ..common.iterators import groupby_to_dict as groupby
from ..common.path import url_to_path
from ..common.serialize import json
from ..common.url import join_url
from ..exceptions import ChannelError, CondaUpgradeError, UnavailableInvalidChannel
from ..gateways.disk.delete import rm_rf
from ..gateways.repodata import (
    CACHE_STATE_SUFFIX,
    CondaRepoInterface,
    RepodataFetch,
    RepodataState,
    cache_fn_url,
    create_cache_dir,
    get_repo_interface,
)
from ..models.channel import Channel, all_channel_urls
from ..models.match_spec import MatchSpec
from ..models.records import PackageRecord

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator
    from typing import Any, Self

    from ..gateways.repodata import RepodataCache, RepoInterface

log = getLogger(__name__)

REPODATA_PICKLE_VERSION = 30
MAX_REPODATA_VERSION = 2
REPODATA_HEADER_RE = b'"(_etag|_mod|_cache_control)":[ ]?"(.*?[^\\\\])"[,}\\s]'


class SubdirDataType(type):
    def __call__(cls, channel: Channel, repodata_fn: str = REPODATA_FN) -> SubdirData:
        assert channel.subdir
        assert not channel.package_filename
        assert type(channel) is Channel
        now = time()
        repodata_fn = repodata_fn or REPODATA_FN
        cache_key = channel.url(with_credentials=True), repodata_fn
        if cache_key in SubdirData._cache_:
            cache_entry = SubdirData._cache_[cache_key]
            if cache_key[0] and cache_key[0].startswith("file://"):
                channel_url = channel.url()
                if channel_url:
                    file_path = url_to_path(channel_url + "/" + repodata_fn)
                    if exists(file_path) and cache_entry._mtime >= getmtime(file_path):
                        return cache_entry
            else:
                return cache_entry
        subdir_data_instance = super().__call__(
            channel, repodata_fn, RepoInterface=get_repo_interface()
        )
        subdir_data_instance._mtime = now
        SubdirData._cache_[cache_key] = subdir_data_instance
        return subdir_data_instance


class PackageRecordList(UserList):
    """
    Lazily convert dicts to PackageRecord.

    This class inherits from the built-in UserList class and provides a way to lazily convert
    dictionaries to PackageRecord objects. It overrides the __getitem__ method to check if the
    item at the given index is a PackageRecord object. If not, it converts the dictionary to a
    PackageRecord object and stores it in the data list.

    :param data: The list of items
    """

    def __getitem__(self, i: int) -> PackageRecord:
        """
        Returns the PackageRecord at index i. If i is a slice, returns a new instance of
        PackageRecordList containing the PackageRecords at the indices in i. If the PackageRecord
        at index i is not already an instance of PackageRecord, it is converted to one and stored
        back in the data list.

        :param i: An integer or slice object indicating the index or indices of the
                  PackageRecord(s) to be returned.
        :return: If i is a slice, returns a new instance of PackageRecordList containing the
                 PackageRecords at the indices in i. If i is an integer, returns the PackageRecord
                 at index i.
        """
        if isinstance(i, slice):
            return self.__class__(self.data[i])
        else:
            record = self.data[i]
            if not isinstance(record, PackageRecord):
                record = PackageRecord(**record)
                self.data[i] = record
            return record


class SubdirData(metaclass=SubdirDataType):
    """
    A class representing the SubdirData.

    This class provides functionality for managing and caching SubdirData instances.

    :param channel: The channel object
    :param repodata_fn: The name of the repodata file. Defaults to REPODATA_FN
    :return: A SubdirData instance.
    """

    _cache_: dict[tuple[str, str], PackageRecordList | SubdirData] = {}

    @classmethod
    def clear_cached_local_channel_data(cls, exclude_file: bool = True) -> None:
        """
        Clear the cached local channel data.

        This method is used to clear the cached local channel data. It is primarily used during
        unit tests to handle changes in the CONDA_USE_ONLY_TAR_BZ2 environment variable during the
        process lifetime.

        :param exclude_file: A flag indicating whether to exclude file:// URLs from the cache.
        """
        # This should only ever be needed during unit tests, when
        # CONDA_USE_ONLY_TAR_BZ2 may change during process lifetime.
        if exclude_file:
            cls._cache_ = {
                k: v for k, v in cls._cache_.items() if not k[0].startswith("file://")
            }
        else:
            cls._cache_.clear()

    @staticmethod
    def query_all(
        package_ref_or_match_spec: MatchSpec | str,
        channels: Iterable[Channel | str] | None = None,
        subdirs: Iterable[str] | None = None,
        repodata_fn: str = REPODATA_FN,
    ) -> tuple[PackageRecord, ...]:
        """
        Execute a query against all repodata instances in the channel/subdir
        matrix.

        :param package_ref_or_match_spec: A `MatchSpec` query object.  A `str`
            will be turned into a      `MatchSpec` automatically.
        :param channels: An iterable of urls for channels or `Channel` objects.
            If None, will fall back to `context.channels`.
        :param subdirs: If None, will fall back to context.subdirs.
        :param repodata_fn: The filename of the repodata.
        :return: A tuple of `PackageRecord` objects.
        """
        # ensure that this is not called by threaded code
        create_cache_dir()
        if channels is None:
            channels = context.channels
        if subdirs is None:
            subdirs = context.subdirs
        channel_urls = all_channel_urls(channels, subdirs=subdirs)
        if context.offline:
            grouped_urls = groupby(lambda url: url.startswith("file://"), channel_urls)
            ignored_urls = grouped_urls.get(False, ())
            if ignored_urls:
                log.info(
                    "Ignoring the following channel urls because mode is offline.%s",
                    dashlist(ignored_urls),
                )
            channel_urls = IndexedSet(grouped_urls.get(True, ()))

        def subdir_query(url: str) -> tuple[PackageRecord, ...]:
            """
            Queries the SubdirData for a given URL and returns a tuple of PackageRecord objects.

            :param url: The URL of the SubdirData to query.
            :return: A tuple of PackageRecord objects representing the query results.
            """
            return tuple(
                SubdirData(Channel(url), repodata_fn=repodata_fn).query(
                    package_ref_or_match_spec
                )
            )

        # TODO test timing with ProcessPoolExecutor
        Executor = (
            DummyExecutor
            if context.debug or context.repodata_threads == 1
            else partial(
                ThreadLimitedThreadPoolExecutor, max_workers=context.repodata_threads
            )
        )
        with Executor() as executor:
            result = tuple(
                chain.from_iterable(executor.map(subdir_query, channel_urls))
            )
        return result

    def query(
        self, package_ref_or_match_spec: str | MatchSpec
    ) -> Iterator[PackageRecord]:
        """
        A function that queries for a specific package reference or MatchSpec object.

        :param package_ref_or_match_spec: The package reference or MatchSpec object to query.
        :yields: PackageRecord objects.
        """
        if not self._loaded:
            self.load()
        param = package_ref_or_match_spec
        if isinstance(param, str):
            param = MatchSpec(param)  # type: ignore
        if isinstance(param, MatchSpec):
            if param.get_exact_value("name"):
                package_name = param.get_exact_value("name")
                for prec in self._iter_records_by_name(package_name):
                    if param.match(prec):
                        yield prec
            else:
                for prec in self.iter_records():
                    if param.match(prec):
                        yield prec
        else:
            assert isinstance(param, PackageRecord)
            for prec in self._iter_records_by_name(param.name):
                if prec == param:
                    yield prec

    def __init__(
        self,
        channel: Channel,
        repodata_fn: str = REPODATA_FN,
        RepoInterface: type[RepoInterface] = CondaRepoInterface,
    ):
        """
        Initializes a new instance of the SubdirData class.

        :param channel: The channel object.
        :param repodata_fn: The repodata filename.
        :param RepoInterface: The RepoInterface class.
        """
        assert channel.subdir
        # metaclass __init__ asserts no package_filename
        if channel.package_filename:  # pragma: no cover
            parts = channel.dump()
            del parts["package_filename"]
            channel = Channel(**parts)
        self.channel = channel
        # disallow None (typing)
        self.url_w_subdir = self.channel.url(with_credentials=False) or ""
        self.url_w_credentials = self.channel.url(with_credentials=True) or ""
        # these can be overriden by repodata.json v2
        self._base_url = self.url_w_subdir
        self._base_url_w_credentials = self.url_w_credentials
        # whether or not to try using the new, trimmed-down repodata
        self.repodata_fn = repodata_fn
        self.RepoInterface = RepoInterface
        self._loaded = False
        self._key_mgr = None

    @property
    def _repo(self) -> RepoInterface:
        """
        Changes as we mutate self.repodata_fn.
        """
        return self.repo_fetch._repo

    @property
    def repo_cache(self) -> RepodataCache:
        """
        Returns the `RepodataCache` object associated with the current instance of `SubdirData`.
        """
        return self.repo_fetch.repo_cache

    @property
    def repo_fetch(self) -> RepodataFetch:
        """
        Object to get repodata. Not cached since self.repodata_fn is mutable.

        Replaces self._repo & self.repo_cache.
        """
        return RepodataFetch(
            Path(self.cache_path_base),
            self.channel,
            self.repodata_fn,
            repo_interface_cls=self.RepoInterface,
        )

    def reload(self) -> Self:
        """
        Update the instance with new information.
        """
        self._loaded = False
        self.load()
        return self

    @property
    def cache_path_base(self) -> str:
        """
        Get the base path for caching the repodata.json file.

        This method returns the base path for caching the repodata.json file. It is used to
        construct the full path for caching the file.
        """
        return join(
            create_cache_dir(),
            splitext(cache_fn_url(self.url_w_credentials, self.repodata_fn))[0],
        )

    @property
    def url_w_repodata_fn(self) -> str:
        """
        Get the URL with the repodata filename.

        This method returns the URL with the repodata filename.
        """
        return self.url_w_subdir + "/" + self.repodata_fn

    @property
    def cache_path_json(self) -> Path:
        """
        Get the path to the cache file.

        This method returns the path to the cache file.
        """
        return Path(
            self.cache_path_base + ("1" if context.use_only_tar_bz2 else "") + ".json"
        )

    @property
    def cache_path_state(self) -> Path:
        """
        Out-of-band etag and other state needed by the RepoInterface.

        Get the path to the cache state file.

        This method returns the path to the cache state file.
        """
        return Path(
            self.cache_path_base
            + ("1" if context.use_only_tar_bz2 else "")
            + CACHE_STATE_SUFFIX
        )

    @property
    def cache_path_pickle(self) -> str:
        """
        Get the path to the cache pickle file.

        This method returns the path to the cache pickle file.
        """
        return self.cache_path_base + ("1" if context.use_only_tar_bz2 else "") + ".q"

    def load(self) -> Self:
        """
        Load the internal state of the SubdirData instance.

        This method loads the internal state of the SubdirData instance.
        """
        _internal_state = self._load()
        if _internal_state.get("repodata_version", 0) > MAX_REPODATA_VERSION:
            raise CondaUpgradeError(
                dals(
                    """
                The current version of conda is too old to read repodata from

                    %s

                (This version only supports repodata_version 1 and 2.)
                Please update conda to use this channel.
                """
                )
                % self.url_w_repodata_fn
            )
        self._base_url = _internal_state.get("base_url", self.url_w_subdir)
        self._base_url_w_credentials = _internal_state.get(
            "base_url_w_credentials", self.url_w_credentials
        )
        self._internal_state = _internal_state
        self._package_records = _internal_state["_package_records"]
        self._names_index = _internal_state["_names_index"]
        # Unused since early 2023:
        self._track_features_index = _internal_state["_track_features_index"]
        self._loaded = True
        return self

    def iter_records(self) -> Iterator[PackageRecord]:
        """
        A function that iterates over package records.

        This function checks if the package records are loaded. If not loaded, it loads them. It
        returns an iterator over the package records. The package_records attribute could
        potentially be replaced with fully-converted UserList data after going through the entire
        list.
        """
        if not self._loaded:
            self.load()
        return iter(self._package_records)
        # could replace self._package_records with fully-converted UserList.data
        # after going through entire list

    def _iter_records_by_name(self, name: str) -> Iterator[PackageRecord]:
        """
        A function that iterates over package records by name.

        This function iterates over package records and yields those whose name matches the given
        name. If include_self is True, it also yields the record with the given name.
        """
        for i in self._names_index[name]:
            yield self._package_records[i]

    def _load(self) -> dict[str, Any]:
        """
        Try to load repodata. If e.g. we are downloading
        `current_repodata.json`, fall back to `repodata.json` when the former is
        unavailable.
        """
        try:
            fetcher = self.repo_fetch
            repodata, state = fetcher.fetch_latest_parsed()
            return self._process_raw_repodata(repodata, state)
        except UnavailableInvalidChannel:
            if self.repodata_fn != REPODATA_FN:
                self.repodata_fn = REPODATA_FN
                return self._load()
            else:
                raise

    def _pickle_me(self) -> None:
        """
        Pickle the object to the specified file.
        """
        try:
            log.debug(
                "Saving pickled state for %s at %s",
                self.url_w_repodata_fn,
                self.cache_path_pickle,
            )
            with open(self.cache_path_pickle, "wb") as fh:
                pickle.dump(self._internal_state, fh, pickle.HIGHEST_PROTOCOL)
        except Exception:
            log.debug("Failed to dump pickled repodata.", exc_info=True)

    def _read_local_repodata(self, state: RepodataState) -> dict[str, Any]:
        """
        Read local repodata from the cache and process it.
        """
        # first try reading pickled data
        _pickled_state = self._read_pickled(state)
        if _pickled_state:
            return _pickled_state

        raw_repodata_str, state = self.repo_fetch.read_cache()
        _internal_state = self._process_raw_repodata_str(raw_repodata_str, state)
        # taken care of by _process_raw_repodata():
        assert self._internal_state is _internal_state
        self._pickle_me()
        return _internal_state

    def _pickle_valid_checks(
        self, pickled_state: dict[str, Any], mod: str, etag: str
    ) -> Iterator[tuple[str, Any, Any]]:
        """
        Throw away the pickle if these don't all match.

        :param pickled_state: The pickled state to compare against.
        :param mod: The modification information to check.
        :param etag: The etag to compare against.
        :yields: Tuples of the form (check_name, pickled_value, current_value).
        """
        yield "_url", pickled_state.get("_url"), self.url_w_credentials
        yield "_schannel", pickled_state.get("_schannel"), self.channel.canonical_name
        yield (
            "_add_pip",
            pickled_state.get("_add_pip"),
            context.add_pip_as_python_dependency,
        )
        yield "_mod", pickled_state.get("_mod"), mod
        yield "_etag", pickled_state.get("_etag"), etag
        yield (
            "_pickle_version",
            pickled_state.get("_pickle_version"),
            REPODATA_PICKLE_VERSION,
        )
        yield "fn", pickled_state.get("fn"), self.repodata_fn

    def _read_pickled(self, state: RepodataState) -> dict[str, Any] | None:
        """
        Read pickled repodata from the cache and process it.

        :param state: The repodata state.
        :return: A dictionary containing the processed pickled repodata, or None if the repodata is
            not pickled.
        """
        if not isinstance(state, RepodataState):
            state = RepodataState(
                self.cache_path_json,
                self.cache_path_state,
                self.repodata_fn,
                dict=state,
            )

        if not isfile(self.cache_path_pickle) or not isfile(self.cache_path_json):
            # Don't trust pickled data if there is no accompanying json data
            return None

        try:
            if isfile(self.cache_path_pickle):
                log.debug("found pickle file %s", self.cache_path_pickle)
            with open(self.cache_path_pickle, "rb") as fh:
                _pickled_state = pickle.load(fh)
        except Exception:
            log.debug("Failed to load pickled repodata.", exc_info=True)
            rm_rf(self.cache_path_pickle)
            return None

        def checks() -> Iterator[tuple[str, str | None, str]]:
            """
            Generate a list of checks to verify the validity of a pickled state.

            :return: A list of tuples, where each tuple contains a check name, the value from the
                pickled state, and the current value.
            """
            return self._pickle_valid_checks(_pickled_state, state.mod, state.etag)

        def _check_pickled_valid() -> Iterator[bool]:
            """
            Generate a generator that yields the results of checking the validity of a pickled
            state.

            :yields: True if the pickled state is valid, False otherwise.
            """
            for _, left, right in checks():
                yield left == right

        if not all(_check_pickled_valid()):
            log.debug(
                "Pickle load validation failed for %s at %s. %r",
                self.url_w_repodata_fn,
                self.cache_path_json,
                tuple(checks()),
            )
            return None

        return _pickled_state

    def _process_raw_repodata_str(
        self,
        raw_repodata_str: str,
        state: RepodataState | None = None,
    ) -> dict[str, Any]:
        """State contains information that was previously in-band in raw_repodata_str.

        Process the raw repodata string and return the processed repodata.

        :param raw_repodata_str: The raw repodata string.
        :return: A dictionary containing the processed repodata.
        """
        json_obj = json.loads(raw_repodata_str or "{}")
        return self._process_raw_repodata(json_obj, state=state)

    def _process_raw_repodata(
        self, repodata: dict[str, Any], state: RepodataState | None = None
    ) -> dict[str, Any]:
        """
        Process the raw repodata dictionary and return the processed repodata.

        :param repodata: The raw repodata dictionary.
        :param state: The repodata state. Defaults to None.
        :return: A dictionary containing the processed repodata.
        """
        if not isinstance(state, RepodataState):
            state = RepodataState(
                self.cache_path_json,
                self.cache_path_state,
                self.repodata_fn,
                dict=state,
            )

        subdir = repodata.get("info", {}).get("subdir") or self.channel.subdir
        assert subdir == self.channel.subdir
        add_pip = context.add_pip_as_python_dependency
        schannel = self.channel.canonical_name

        self._package_records = _package_records = PackageRecordList()
        self._names_index = _names_index = defaultdict(list)
        self._track_features_index = _track_features_index = defaultdict(list)
        base_url = self._get_base_url(repodata, with_credentials=False)
        base_url_w_credentials = self._get_base_url(repodata, with_credentials=True)

        _internal_state = {
            "channel": self.channel,
            "url_w_subdir": self.url_w_subdir,
            "url_w_credentials": self.url_w_credentials,
            "base_url": base_url,
            "base_url_w_credentials": base_url_w_credentials,
            "cache_path_base": self.cache_path_base,
            "fn": self.repodata_fn,
            "_package_records": _package_records,
            "_names_index": _names_index,
            "_track_features_index": _track_features_index,
            "_etag": state.get("_etag"),
            "_mod": state.get("_mod"),
            "_cache_control": state.get("_cache_control"),
            "_url": state.get("_url"),
            "_add_pip": add_pip,
            "_pickle_version": REPODATA_PICKLE_VERSION,
            "_schannel": schannel,
            "repodata_version": state.get("repodata_version", 0),
        }
        if _internal_state["repodata_version"] > MAX_REPODATA_VERSION:
            raise CondaUpgradeError(
                dals(
                    """
                The current version of conda is too old to read repodata from

                    %s

                (This version only supports repodata_version 1 and 2.)
                Please update conda to use this channel.
                """
                )
                % self.url_w_subdir
            )

        meta_in_common = {  # just need to make this once, then apply with .update()
            "arch": repodata.get("info", {}).get("arch"),
            "channel": self.channel,
            "platform": repodata.get("info", {}).get("platform"),
            "schannel": schannel,
            "subdir": subdir,
        }

        legacy_packages = repodata.get("packages", {})
        conda_packages = (
            {} if context.use_only_tar_bz2 else repodata.get("packages.conda", {})
        )

        _tar_bz2 = CONDA_PACKAGE_EXTENSION_V1
        use_these_legacy_keys = set(legacy_packages.keys()) - {
            k[:-6] + _tar_bz2 for k in conda_packages.keys()
        }

        for group, copy_legacy_md5 in (
            (conda_packages.items(), True),
            (((k, legacy_packages[k]) for k in use_these_legacy_keys), False),
        ):
            for fn, info in group:
                if copy_legacy_md5:
                    counterpart = f"{fn[: -len('.conda')]}.tar.bz2"
                    if counterpart in legacy_packages:
                        info["legacy_bz2_md5"] = legacy_packages[counterpart].get("md5")
                        info["legacy_bz2_size"] = legacy_packages[counterpart].get(
                            "size"
                        )
                if (
                    add_pip
                    and info["name"] == "python"
                    and info["version"].startswith(("2.", "3."))
                ):
                    info["depends"].append("pip")
                info.update(meta_in_common)
                if info.get("record_version", 0) > 1:
                    log.debug(
                        "Ignoring record_version %d from %s",
                        info["record_version"],
                        info["url"],
                    )
                    continue

                # lazy
                # package_record = PackageRecord(**info)
                info["fn"] = fn
                info["url"] = join_url(base_url_w_credentials, fn)
                _package_records.append(info)
                record_index = len(_package_records) - 1
                _names_index[info["name"]].append(record_index)

        self._internal_state = _internal_state
        return _internal_state

    def _get_base_url(self, repodata: dict, with_credentials: bool = True) -> str:
        """
        In repodata_version=1, .tar.bz2 and .conda artifacts are assumed to
        be colocated next to repodata.json, in the same server and directory.

        In repodata_version=2, repodata.json files can define a 'base_url' field
        to override that default assumption. See CEP-15 for more details.

        This method deals with both cases and returns the appropriate value.

        Get the base URL for the given endpoint.

        :param endpoint: The endpoint for which the base URL is needed.
        :return: The base URL corresponding to the provided endpoint.
        """
        maybe_base_url = repodata.get("info", {}).get("base_url")
        if maybe_base_url:  # repodata defines base_url field
            try:
                base_url_parts = Channel(maybe_base_url).dump()
            except ValueError as exc:
                raise ChannelError(
                    f"Subdir for {self.channel.canonical_name} at url '{self.url_w_subdir}' "
                    "has invalid 'base_url'"
                ) from exc
            if with_credentials and self.url_w_credentials != self.url_w_subdir:
                # We don't check for .token or .auth because those are not well defined
                # in multichannel objects. It's safer to compare the resulting URLs.
                # Note that base_url is assumed to have the same authentication as the repodata
                channel_parts = self.channel.dump()
                for key in ("auth", "token"):
                    if base_url_parts.get(key):
                        raise ChannelError(
                            f"'{self.url_w_subdir}' has 'base_url' with credentials. "
                            "This is not supported."
                        )
                    channel_creds = channel_parts.get(key)
                    if channel_creds:
                        base_url_parts[key] = channel_creds
                return Channel(**base_url_parts).url(with_credentials=True)
            return maybe_base_url
        if with_credentials:
            return self.url_w_credentials
        return self.url_w_subdir
