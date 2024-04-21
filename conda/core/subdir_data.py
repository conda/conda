# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Tools for managing a subdir's repodata.json."""

from __future__ import annotations

import json
import pickle
from collections import UserList, defaultdict
from functools import partial
from itertools import chain
from logging import getLogger
from os.path import exists, join, splitext
from pathlib import Path
from time import time
from typing import TYPE_CHECKING

from boltons.setutils import IndexedSet
from genericpath import getmtime, isfile

from ..auxlib.ish import dals
from ..base.constants import CONDA_PACKAGE_EXTENSION_V1, REPODATA_FN
from ..base.context import context
from ..common.io import DummyExecutor, ThreadLimitedThreadPoolExecutor, dashlist
from ..common.iterators import groupby_to_dict as groupby
from ..common.path import url_to_path
from ..common.url import join_url
from ..deprecations import deprecated
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
from ..gateways.repodata import (
    get_cache_control_max_age as _get_cache_control_max_age,
)
from ..models.channel import Channel, all_channel_urls
from ..models.match_spec import MatchSpec
from ..models.records import PackageRecord

if TYPE_CHECKING:
    from typing import Any, Generator, Iterable, Iterator, Optional

    from ..gateways.repodata import RepodataCache, RepoInterface
    from .index import PackageRef

log = getLogger(__name__)

REPODATA_PICKLE_VERSION = 30
MAX_REPODATA_VERSION = 2
REPODATA_HEADER_RE = b'"(_etag|_mod|_cache_control)":[ ]?"(.*?[^\\\\])"[,}\\s]'  # NOQA


@deprecated(
    "24.3",
    "24.9",
    addendum="Use `conda.gateways.repodata.get_cache_control_max_age` instead.",
)
def get_cache_control_max_age(cache_control_value: str) -> int:
    """
    A function to get the cache control max age based on the cache control value provided.

    :param cache_control_value: The cache control value to determine the max age from.
    :type cache_control_value: str
    :return: The maximum age for the cache control value.
    :rtype: int
    """
    return _get_cache_control_max_age(cache_control_value)


class SubdirDataType(type):
    """
    A class representing the SubdirDataType.

    :param channel: The channel object.
    :type channel: Channel
    :param repodata_fn: The name of the repodata file. Defaults to REPODATA_FN.
    :type repodata_fn: str
    :return: A SubdirData instance.
    :rtype: SubdirData
    """

    def __call__(cls, channel: Channel, repodata_fn: str = REPODATA_FN) -> SubdirData:
        """
        Returns a SubdirData instance for the given channel and repodata_fn.

        :param channel: The channel object.
        :type channel: Channel
        :param repodata_fn: The name of the repodata file. Defaults to REPODATA_FN.
        :type repodata_fn: str
        :return: A SubdirData instance.
        :rtype: SubdirData
        """
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

    :param data: The list of items.
    :type data: List[dict[str, Any] | PackageRecord]
    """

    def __getitem__(self, i: int) -> PackageRecord:
        """
        Returns the PackageRecord at index i. If i is a slice, returns a new instance of
        PackageRecordList containing the PackageRecords at the indices in i. If the PackageRecord
        at index i is not already an instance of PackageRecord, it is converted to one and stored
        back in the data list.

        :param i: An integer or slice object indicating the index or indices of the PackageRecord(s)
                  to be returned.
        :type i: int or slice
        :return: If i is a slice, returns a new instance of PackageRecordList containing the
                 PackageRecords at the indices in i. If i is an integer, returns the PackageRecord
                 at index i.
        :rtype: PackageRecord or PackageRecordList
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

    :param channel: The channel object.
    :type channel: Channel
    :param repodata_fn: The name of the repodata file. Defaults to REPODATA_FN.
    :type repodata_fn: str
    :return: A SubdirData instance.
    :rtype: SubdirData
    """

    _cache_: dict[tuple[str, str], PackageRecordList | SubdirData] = {}

    @classmethod
    def clear_cached_local_channel_data(cls, exclude_file: bool = True) -> None:
        """
        Clear the cached local channel data.

        This method is used to clear the cached local channel data. It is primarily used during unit tests to handle
        changes in the CONDA_USE_ONLY_TAR_BZ2 environment variable during the process lifetime.

        :param exclude_file: A flag indicating whether to exclude file:// URLs from the cache. Defaults to True.
        :type exclude_file: bool
        :return: None
        :rtype: None
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
        package_ref_or_match_spec: PackageRef | MatchSpec | str,
        channels: Optional[Iterable[Channel | str]] = None,
        subdirs: Optional[Iterable[str]] = None,
        repodata_fn: str = REPODATA_FN,
    ) -> tuple[PackageRecord, ...]:
        """
        Executes a query against all repodata instances in the channel/subdir matrix.

        :param package_ref_or_match_spec: Either an exact `PackageRef` to match against, or a `MatchSpec` query object.  A `str` will be turned into a `MatchSpec` automatically.
        :type package_ref_or_match_spec: PackageRef | MatchSpec | str
        :param channels: An iterable of urls for channels or `Channel` objects. If None, will fall back to context.channels.
        :type channels: Optional[Iterable[Channel | str]]
        :param subdirs: If None, will fall back to context.subdirs.
        :type subdirs: Optional[Iterable[str]]
        :param repodata_fn: The filename of the repodata.
        :type repodata_fn: str
        :return: A tuple of `PackageRecord` objects.
        :rtype: tuple[PackageRecord, ...]
        """

        from .index import check_allowlist  # TODO: fix in-line import

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

        check_allowlist(channel_urls)

        def subdir_query(url: str) -> tuple[PackageRecord, ...]:
            """
            Queries the SubdirData for a given URL and returns a tuple of PackageRecord objects.

            :param url: The URL of the SubdirData to query.
            :type url: str
            :return: A tuple of PackageRecord objects representing the query results.
            :rtype: tuple[PackageRecord, ...]
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
    ) -> Generator[PackageRecord, None, None]:
        """
        A function that queries for a specific package reference or MatchSpec object.

        :param package_ref_or_match_spec: The package reference or MatchSpec object to query.
        :type package_ref_or_match_spec: str | MatchSpec]
        :return: A generator yielding PackageRecord objects.
        :rtype: Generator[PackageRecord, None, None]
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
    ) -> None:
        """
        Initializes a new instance of the SubdirData class.

        :param channel: The channel object.
        :type channel: Channel
        :param repodata_fn: The repodata filename.
        :type repodata_fn: str
        :param RepoInterface: The RepoInterface class.
        :type RepoInterface: Type[RepoInterface]
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

        Returns the RepoInterface object.

        :return: The RepoInterface object.
        :rtype: RepoInterface
        """
        return self.repo_fetch._repo

    @property
    def repo_cache(self) -> RepodataCache:
        """
        Returns the `RepodataCache` object associated with the current instance of `SubdirData`.

        :return: The `RepodataCache` object.
        :rtype: RepodataCache
        """
        return self.repo_fetch.repo_cache

    @property
    def repo_fetch(self) -> RepodataFetch:
        """
        Object to get repodata. Not cached since self.repodata_fn is mutable.

        Replaces self._repo & self.repo_cache.

        :return: The `RepodataFetch` object.
        :rtype: RepodataFetch
        """
        return RepodataFetch(
            Path(self.cache_path_base),
            self.channel,
            self.repodata_fn,
            repo_interface_cls=self.RepoInterface,
        )

    def reload(self) -> SubdirData:
        """
        Update the instance with new information.

        :return: An instance of the SubdirData class.
        :rtype: SubdirData
        """
        self._loaded = False
        self.load()
        return self

    @property
    def cache_path_base(self) -> str:
        """
        Get the base path for caching the repodata.json file.

        This method returns the base path for caching the repodata.json file. It is used to construct the full path for caching the file.

        :return: The base path for caching the repodata.json file.
        :rtype: str
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

        :return: The URL with the repodata filename.
        :rtype: str
        """
        return self.url_w_subdir + "/" + self.repodata_fn

    @property
    def cache_path_json(self) -> str:
        """
        Get the path to the cache file.

        This method returns the path to the cache file.

        :return: The path to the cache file.
        :rtype: str
        """
        return Path(
            self.cache_path_base + ("1" if context.use_only_tar_bz2 else "") + ".json"
        )

    @property
    def cache_path_state(self) -> str:
        """
        Out-of-band etag and other state needed by the RepoInterface.

        Get the path to the cache state file.

        This method returns the path to the cache state file.

        :return: The path to the cache state file.
        :rtype: str
        """
        return Path(
            self.cache_path_base
            + ("1" if context.use_only_tar_bz2 else "")
            + CACHE_STATE_SUFFIX
        )

    @property
    def cache_path_pickle(self) -> Path:
        """
        Get the path to the cache pickle file.

        This method returns the path to the cache pickle file.

        :return: The path to the cache pickle file.
        :rtype: Path
        """
        return self.cache_path_base + ("1" if context.use_only_tar_bz2 else "") + ".q"

    def load(self) -> None:
        """
        Load the internal state of the SubdirData instance.

        This method loads the internal state of the SubdirData instance.

        :return: None
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

        This function checks if the package records are loaded. If not loaded, it loads them.
        It returns an iterator over the package records. The package_records attribute could potentially be
        replaced with fully-converted UserList data after going through the entire list.

        :return: An iterator over the package records.
        :rtype: Iterator[PackageRecord]
        """
        if not self._loaded:
            self.load()
        return iter(self._package_records)
        # could replace self._package_records with fully-converted UserList.data
        # after going through entire list

    def _iter_records_by_name(self, name: str) -> Iterator[PackageRecord]:
        """
        A function that iterates over package records by name.

        This function iterates over package records and yields those whose name matches the given name.
        If include_self is True, it also yields the record with the given name.

        :param name: The name to match against.
        :type name: str
        :rtype: Iterator[PackageRecord]
        """
        for i in self._names_index[name]:
            yield self._package_records[i]

    def _load(self) -> dict[str, Any]:
        """
        Try to load repodata. If e.g. we are downloading
        `current_repodata.json`, fall back to `repodata.json` when the former is
        unavailable.

        :return: A dictionary containing the loaded repodata.
        :rtype: dict[str, Any]
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

        :return: None
        :rtype: None
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

        :param state: The repodata state.
        :type state: RepodataState
        :return: A dictionary containing the processed repodata.
        :rtype: dict[str, Any]
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
    ) -> Generator[tuple[str, Any, Any], None, None]:
        """
        Throw away the pickle if these don't all match.

        :param pickled_state: The pickled state to compare against.
        :type pickled_state: dict[str, Any]
        :param mod: The modification information to check.
        :type mod: str
        :param etag: The etag to compare against.
        :type etag: str
        :return: A generator that yields tuples of the form (check_name, pickled_value, current_value).
        :rtype: Generator[tuple[str, Any, Any], None, None]
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

    def _read_pickled(self, state: RepodataState) -> Optional[dict[str, Any]]:
        """
        Read pickled repodata from the cache and process it.

        :param state: The repodata state.
        :type state: RepodataState
        :return: A dictionary containing the processed pickled repodata, or None if the repodata is not pickled.
        :rtype: Optional[dict[str, Any]]
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

        def checks():
            """
            Generate a list of checks to verify the validity of a pickled state.

            :return: A list of tuples, where each tuple contains a check name, the value from the pickled state, and the current value.
            :rtype: List[tuple[str, Any, Any]]
            """
            return self._pickle_valid_checks(_pickled_state, state.mod, state.etag)

        def _check_pickled_valid():
            """
            Generate a generator that yields the results of checking the validity of a pickled state.

            :yields: True if the pickled state is valid, False otherwise.
            :yield type: bool

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
    ) -> Iterator[tuple[str, str, str]]:
        """State contains information that was previously in-band in raw_repodata_str.

        Process the raw repodata string and yield the results of checking the validity of a pickled state.

        :param raw_repodata_str: The raw repodata string.
        :type raw_repodata_str: str

        :return: An iterator that yields tuples containing the results of checking the validity of a pickled state.
                Each tuple contains three strings: the left side of the comparison, the right side of the comparison,
                and the result of the comparison (True if equal, False otherwise).
        :rtype: Iterator[tuple[str, str, str]]
        """
        json_obj = json.loads(raw_repodata_str or "{}")
        return self._process_raw_repodata(json_obj, state=state)

    def _process_raw_repodata(
        self, repodata: dict[str, Any], state: Optional[RepodataState] = None
    ) -> dict[str, Any]:
        """
        Process the raw repodata dictionary and return the processed repodata.

        :param repodata: The raw repodata dictionary.
        :type repodata: dict[str, Any]
        :param state: The repodata state. Defaults to None.
        :type state: Optional[RepodataState]
        :return: A dictionary containing the processed repodata.
        :rtype: dict[str, Any]
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
                    counterpart = fn.replace(".conda", ".tar.bz2")
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
        :type endpoint: str

        :return: The base URL corresponding to the provided endpoint.
        :rtype: str
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


def make_feature_record(feature_name: str) -> PackageRecord:
    """
    Create a feature record based on the given feature name.

    :param feature_name: The name of the feature.
    :type feature_name: str

    :return: The created PackageRecord for the feature.
    :rtype: PackageRecord
    """
    # necessary for the SAT solver to do the right thing with features
    pkg_name = "%s@" % feature_name
    return PackageRecord(
        name=pkg_name,
        version="0",
        build="0",
        channel="@",
        subdir=context.subdir,
        md5="12345678901234567890123456789012",
        track_features=(feature_name,),
        build_number=0,
        fn=pkg_name,
    )
