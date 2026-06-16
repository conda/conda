# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Models for sharded repodata, and to make monolithic repodata look like sharded
repodata.
"""

from __future__ import annotations

import abc
import concurrent.futures
import json  # noqa
import logging
from collections import defaultdict
from typing import TYPE_CHECKING

import msgpack

import conda.exceptions
import conda.gateways.repodata
from conda.base.constants import REPODATA_SHARDS_FN
from conda.base.context import context
from conda.core.subdir_data import SubdirData
from conda.gateways.connection.session import get_session
from conda.gateways.repodata import (
    _add_http_value_to_dict,
    conda_http_errors,
)
from conda.models.channel import Channel

from ..zstd import capped_decompress
from . import cache
from .misc import (
    _is_http_error_most_400_codes,
    _safe_urljoin_with_slash,
    _shards_connections,
    ensure_hex_hash,
    spec_to_package_name,
)

log = logging.getLogger(__name__)


if TYPE_CHECKING:
    from collections.abc import Iterable, KeysView, Sequence

    from requests import Response

    from conda.gateways.repodata import RepodataCache

    from .typing import RepodataDict, ShardDict, ShardsIndexDict

ZSTD_MAX_SHARD_SIZE = (
    2**20 * 16
)  # maximum size necessary when compressed data has no size header


# For reference, the largest shard "conda-forge/linux-64/vim" is 2608283 bytes
# or < 2**19*5 decompressed (486155 bytes compressed); the index is 575219 bytes
# decompressed (514039 bytes compressed) and is mostly uncompressible hash data.


class ShardFetch:
    """
    Wrapper class that encapsulates fetching and caching of individual shards.

    Handles deferred fetching: shards can be requested via this class but will
    only be actually retrieved from the network when fetch() is called.
    This allows batching and coordinating shard retrieval across multiple channels.
    """

    def __init__(
        self,
        shardbase: ShardBase,
        package: str,
        shard_cache: cache.ShardCache | None = None,
    ):
        """
        Initialize a ShardFetch wrapper.

        Args:
            shardbase: The ShardBase (Shards or ShardLike) instance
            package: The package name to fetch
            shard_cache: Optional cache to use for storage (required for Shards)
        """
        self.shardbase = shardbase
        self.package = package
        self.url = shardbase.shard_url(package)
        self.shard_cache = shard_cache
        self._shard: ShardDict | None = None
        self._fetched = False

    def fetch(self) -> ShardDict:
        """
        Fetch the shard from the network or return cached result.

        For Shards, performs the actual network fetch.
        For ShardLike, returns the shard immediately since it's in memory.
        """
        if not self._fetched:
            if isinstance(self.shardbase, Shards):
                self._shard = self._fetch_from_shards()
            else:  # ShardLike
                self._shard = self.shardbase.visit_package(self.package)
            self._fetched = True
        return self._shard

    def _fetch_from_shards(self) -> ShardDict:
        """
        Fetch a single shard from a Shards instance.
        """
        return self._fetch_shards_impl([self.package])[self.package]

    def _fetch_shards_impl(self, packages: Iterable[str]) -> dict[str, ShardDict]:
        """
        Fetch multiple shards for a Shards instance.

        Implements the core fetching logic for Shards, handling network requests,
        caching, and decompression.
        """
        shards = self.shardbase  # type: ignore[assignment]
        results = {}

        def fetch(s, url, package_to_fetch):
            timeout = (
                context.remote_connect_timeout_secs,
                context.remote_read_timeout_secs,
            )
            response = s.get(url, timeout=timeout)
            response.raise_for_status()
            data = response.content

            return cache.AnnotatedRawShard(
                url=url, package=package_to_fetch, compressed_shard=data
            )

        packages = sorted(list(packages))
        urls_packages = {}  # package shards to fetch
        for package in packages:
            if package in shards.visited:
                results[package] = shards.visited[package]
            else:
                urls_packages[shards.shard_url(package)] = package

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=_shards_connections()
        ) as executor:
            futures = {
                executor.submit(fetch, shards.session, url, package): (url, package)
                for url, package in urls_packages.items()
                if package not in results
            }
            for future in concurrent.futures.as_completed(futures):
                log.debug(". %s", futures[future])
                url, package = futures[future]
                self._process_fetch_result(future, url, package, results, shards)

        shards.visited.update(results)

        return results

    def _process_fetch_result(self, future, url, package, results, shards):
        """
        Process a single fetched shard result.
        """
        # Cache must be provided for Shards instances
        if self.shard_cache is None:
            raise ValueError("shard_cache is required for fetching from Shards")

        with conda_http_errors(url, package):
            fetch_result = future.result()

        # Decompress and save record
        results[fetch_result.package] = msgpack.loads(
            capped_decompress(
                fetch_result.compressed_shard, max_output_size=ZSTD_MAX_SHARD_SIZE
            )
        )
        self.shard_cache.insert(fetch_result)

    @staticmethod
    def fetch_batch(shard_fetches: Iterable[ShardFetch]) -> None:
        """
        Batch fetch multiple ShardFetch objects, grouping by ShardBase.

        This efficiently fetches shards from multiple sources by grouping
        requests by their ShardBase instance and making coordinated network calls.
        """
        # Group by shardbase to batch fetch calls
        shard_packages: dict[ShardBase, list[str]] = defaultdict(list)
        shard_fetches_by_pkg: dict[tuple[ShardBase, str], ShardFetch] = {}

        for shard_fetch in shard_fetches:
            shard_packages[shard_fetch.shardbase].append(shard_fetch.package)
            shard_fetches_by_pkg[(shard_fetch.shardbase, shard_fetch.package)] = (
                shard_fetch
            )

        # Fetch all packages for each shardbase
        for shardbase, packages in shard_packages.items():
            if isinstance(shardbase, Shards):
                # Use the first ShardFetch to do the actual fetching
                first_fetch = shard_fetches_by_pkg[(shardbase, packages[0])]
                fetched = first_fetch._fetch_shards_impl(packages)

                # Mark all as fetched and store results
                for package, shard in fetched.items():
                    shard_fetch = shard_fetches_by_pkg[(shardbase, package)]
                    shard_fetch._shard = shard
                    shard_fetch._fetched = True


def shard_mentioned_packages(
    shard: ShardDict,
    extra: Iterable[str] = (),
    spec_to_package_name=spec_to_package_name,
    repodata_version: int = 1,
) -> Iterable[str]:
    """
    Return all dependency names mentioned in a shard, not including the shard's
    own package name.
    """
    unique_specs: set[str] = set()

    def _yield_record(record):
        ensure_hex_hash(record)  # otherwise we could do this at serialization
        for spec in record.get("depends", ()):
            if spec not in unique_specs:
                unique_specs.add(spec)
                name = spec_to_package_name(spec)
                if name is not None:
                    yield name  # not much improvement from only yielding unique names

    for record in shard["packages"].values():
        yield from _yield_record(record)
    for record in shard["packages.conda"].values():
        yield from _yield_record(record)
    if repodata_version >= 3 and (v3_data := shard.get("v3")):
        for group in v3_data.values():
            for record in group.values():
                yield from _yield_record(record)
    yield from extra


class ShardBase(abc.ABC):
    """
    Abstract base class for shard-like objects.

    Defines the common interface for both sharded repodata (Shards)
    and monolithic repodata presented as shards (ShardLike).
    """

    url: str
    repodata_no_packages: RepodataDict
    visited: dict[str, ShardDict | None]
    _base_url: str

    @property
    @abc.abstractmethod
    def package_names(self) -> KeysView[str]:
        """Return the names of all packages available in this shard collection."""
        ...

    @property
    def base_url(self) -> str:
        """
        Return self.url joined with base_url from repodata, or self.url if no
        base_url was present. Packages are found here.

        Note base_url can be a relative or an absolute url.
        Uses _safe_urljoin_with_slash to handle non-HTTP schemes (s3://, etc.).
        """
        return _safe_urljoin_with_slash(self.url, self._base_url)

    def __contains__(self, package: str) -> bool:
        """Check if a package is available in this shard collection."""
        return package in self.package_names

    @abc.abstractmethod
    def shard_url(self, package: str) -> str:
        """
        Return shard URL for a given package. For monolithic repodata, should
        not be fetched but is a unique identifier.

        Raise KeyError if package is not in the index.
        """
        ...

    @abc.abstractmethod
    def shard_loaded(self, package: str) -> bool:
        """
        Return True if the given package's shard is in memory.
        """
        ...

    def visit_package(self, package: str) -> ShardDict:
        """
        Return a shard that is already loaded in memory and mark as visited.
        """
        ...

    def visit_shard(self, package: str, shard: ShardDict):
        """
        Store new shard data in the visited dict.
        """
        self.visited[package] = shard

    def build_repodata(self) -> RepodataDict:
        """
        Return monolithic repodata including all visited shards.

        Does not return "v3" repodata.

        Prefer iter_records_v3() over this method.
        """
        repodata: RepodataDict = {
            **self.repodata_no_packages,
            "packages": {},
            "packages.conda": {},
        }
        for _, shard in self.visited.items():
            if shard is None:
                continue  # recorded visited but not available shards
            for package_group in ("packages", "packages.conda"):
                repodata[package_group].update(shard[package_group])
        return repodata

    def iter_records(self) -> Iterable[tuple[str, dict]]:
        """
        Yield (filename, record) tuples for all packages in visited shards.
        """
        for (filename, section), record in self.iter_records_v3():
            if section not in ("packages", "packages.conda"):
                continue
            yield filename, record

    def iter_records_v3(self) -> Iterable[tuple[tuple[str, str], dict]]:
        """
        Yield ((key, section), record) tuples for all packages in visited
        shards.

        Section can be: "packages" for .tar.bz2 packages, "packages.conda"
        for .conda packages, "v3.whl", "v3.conda", "v3.tar.bz2" for v3 packages.

        key is the same as the filename for "packages", "packages.conda" but is
        different from the filename for v3 packages.
        """
        for shard in self.visited.values():
            if shard is None:
                continue
            # Classic packages
            for package_group in ("packages", "packages.conda"):
                for key, record in shard.get(package_group, {}).items():
                    yield (key, package_group), record
            # v3 packages (iter_records() method depends on these coming last)
            for section_name, group in shard.get("v3", {}).items():
                v3_section = f"v3.{section_name}"
                for key, record in group.items():
                    yield (key, v3_section), record


class ShardLike(ShardBase):
    """
    Present a "classic" repodata.json as per-package shards.
    """

    def __init__(self, repodata: RepodataDict, url: str = ""):
        """
        url: must be unique for all ShardLike used together.
        """
        self.repodata_no_packages: RepodataDict = {
            **repodata,
            "packages": {},
            "packages.conda": {},
        }
        all_packages = {
            "packages": repodata.get("packages", {}),
            "packages.conda": repodata.get("packages.conda", {}),
        }
        self.url = url

        shards = defaultdict(lambda: {"packages": {}, "packages.conda": {}})

        for group_name, group in all_packages.items():
            for package, record in group.items():
                name = record["name"]
                shards[name][group_name][package] = record

        # defaultdict behavior no longer wanted
        self.shards: dict[str, ShardDict] = dict(shards)  # type: ignore

        # used to write out repodata subset
        self.visited: dict[str, ShardDict | None] = {}

        # alternate location for packages, if not self.url
        try:
            base_url = self.repodata_no_packages["info"]["base_url"]
            if not isinstance(base_url, str):
                log.warning(
                    'repodata["info"]["base_url"] was not str(), got %s',
                    type(base_url),
                )
                raise TypeError()
            self._base_url = base_url
        except KeyError:
            self._base_url = ""

    def __repr__(self):
        left, right = super().__repr__().split(maxsplit=1)
        return f"{left} {self.url} {right}"

    @property
    def package_names(self) -> KeysView[str]:
        return self.shards.keys()

    def shard_url(self, package: str) -> str:
        """
        Return shard URL for a given package.

        Raise KeyError if package is not in the index.
        """
        self.shards[package]
        return f"{self.url}#{package}"

    def shard_loaded(self, package: str) -> bool:
        """
        Return True if the given package's shard is in memory.
        """
        return package in self.shards

    def visit_package(self, package: str) -> ShardDict:
        """
        Return a shard that is already in memory and mark as visited.
        """
        shard = self.shards[package]
        self.visited[package] = self.shards[package]
        return shard


def _shards_base_url(url, shards_base_url) -> str:
    """
    Return shards_base_url joined with base_url and url.
    Note shards_base_url can be a relative or an absolute url.
    Uses _safe_urljoin_with_slash to handle non-HTTP schemes (s3://, etc.).
    """
    if shards_base_url and not shards_base_url.endswith("/"):
        shards_base_url += "/"
    return _safe_urljoin_with_slash(url, shards_base_url)


class Shards(ShardBase):
    """
    Handle repodata_shards.msgpack.zst and individual per-package shards.
    """

    _shards_base_url: str

    def __init__(
        self,
        shards_index: ShardsIndexDict,
        url: str,
    ):
        """
        Args:
            shards_index: raw parsed msgpack dict. Don't change it or base_url,
            shards_base_url will be wrong.
            url: URL of repodata_shards.msgpack.zst
        """
        self.shards_index = shards_index
        self.url = url

        # https://github.com/conda/conda-index/pull/209 ensures that sharded
        # repodata will always include base_url, even if it is an empty string;
        # rattler/pixi require these keys.
        self._base_url = shards_index["info"]["base_url"]

        # doesn't track changes to self.shards_index
        self._shards_base_url = _shards_base_url(
            self.url, self.shards_index["info"].get("shards_base_url", "")
        )

        # Use the channel's base URL to share session amongst subdir locations
        channel_base_url = Channel(self.shards_base_url).base_url
        self.session = get_session(channel_base_url)

        self.repodata_no_packages = {
            "info": shards_index["info"],
            "packages": {},
            "packages.conda": {},
            "repodata_version": 2,
        }

        # used to write out repodata subset
        # not used in traversal algorithm
        self.visited: dict[str, ShardDict | None] = {}

        self._shard_url_cache: dict[str, str] = {}

    @property
    def package_names(self):
        return self.packages_index.keys()

    @property
    def packages_index(self):
        return self.shards_index["shards"]

    @property
    def shards_base_url(self) -> str:
        """
        Return self.url joined with shards_base_url.
        Note shards_base_url can be a relative or an absolute url.
        """
        return self._shards_base_url

    def shard_url(self, package: str) -> str:
        """
        Return shard URL for a given package.

        Raise KeyError if package is not in the index.
        """
        if cached := self._shard_url_cache.get(package):
            return cached
        shard_name = f"{bytes(self.packages_index[package]).hex()}.msgpack.zst"
        # "Individual shards are stored under the URL <shards_base_url><sha256>.msgpack.zst"
        url = f"{self.shards_base_url}{shard_name}"
        self._shard_url_cache[package] = url
        return url

    def shard_loaded(self, package: str) -> bool:
        """
        Return True if the given package's shard is in memory.
        """
        return package in self.visited

    def visit_package(self, package: str) -> ShardDict:
        """
        Return a shard that is already in memory and mark as visited.
        """
        shard = self.visited[package]
        return shard


def _repodata_shards(url, cache: RepodataCache) -> bytes:
    """
    Fetch shards index with cache.

    Update cache state.

    Return shards data, either newly fetched or from cache.

    In offline mode, returns cached data even if expired. If no cache exists
    in offline mode, raises RepodataIsEmpty to signal unavailability.
    """
    # In offline mode, return cached data if available, even if expired
    if context.offline:
        if cache.cache_path_shards.exists():
            return cache.cache_path_shards.read_bytes()
        else:
            # In offline mode with no cache, signal that shards are not available.
            # The caller (fetch_shards_index) catches RepodataIsEmpty and falls back to non-sharded repodata.
            raise conda.gateways.repodata.RepodataIsEmpty(
                url, status_code=404, response=None
            )

    session = get_session(url)

    state = cache.state
    headers = {}
    etag = state.etag
    last_modified = state.mod
    if etag:
        headers["If-None-Match"] = str(etag)
    if last_modified:
        headers["If-Modified-Since"] = str(last_modified)

    with conda_http_errors(url, REPODATA_SHARDS_FN):
        timeout = (
            context.remote_connect_timeout_secs,
            context.remote_read_timeout_secs,
        )
        response: Response = session.get(
            url, headers=headers, proxies=session.proxies, timeout=timeout
        )
        response.raise_for_status()
        response_bytes = response.content

    if response.status_code == 304:
        # should we save cache-control to state here to put another n
        # seconds on the "make a remote request" clock and/or touch cache
        # mtime
        #
        # Hold the cache lock while reading: RepodataCache.replace() does
        # unlink()+rename() under this same lock, so without it a concurrent
        # writer can briefly remove the file between those two operations,
        # causing FileNotFoundError on Windows.
        with cache.lock("r+"):
            return cache.cache_path_shards.read_bytes()

    saved_fields = {conda.gateways.repodata.URL_KEY: url}
    for header, key in (
        ("Etag", conda.gateways.repodata.ETAG_KEY),
        (
            "Last-Modified",
            conda.gateways.repodata.LAST_MODIFIED_KEY,
        ),
        ("Cache-Control", conda.gateways.repodata.CACHE_CONTROL_KEY),
    ):
        _add_http_value_to_dict(response, header, saved_fields, key)

    state.update(saved_fields)

    # should we return the response and let caller save cache data to state?
    return response_bytes


# Like conda.gateways.repodata.jlap.fetch. If this returns True, then we mark
# shards as not supported; otherwise, we will check again next time.


def fetch_shards_index(sd: SubdirData) -> Shards | None:
    """
    Check a SubdirData's URL for shards.

    Return shards index bytes from cache or network.
    Return None if not found; caller should fetch normal repodata.

    TODO: If this function fails to retrieve the sharded repodata index file, it will
          mark it is as not supporting this feature in cache. This can problematic
          because sometimes server errors can happen which will lead it to wrongly
          assuming the channel doesn't support sharding. We need to rethink our
          logic for determining shard support.
    """

    fetch = sd.repo_fetch
    repo_cache = fetch.repo_cache

    # repo_cache.load_state() will clear the file on JSONDecodeError but cache.load()
    # will raise the exception.
    # repo_cache.load_state(
    #     binary=True
    # )  # won't succeed when .msgpack.zst is missing as it wants to compare the timestamp (returns empty state)

    # Load state ourselves to avoid clearing when binary cached data is missing.
    # If we fall back to monolithic repodata.json, the standard fetch code will
    # load the state again in text mode.
    try:
        with repo_cache.lock("r+") as state_file:
            # cannot use pathlib.read_text / write_text on any locked file, as
            # it will release the lock early
            state = json.loads(state_file.read())
            repo_cache.state.update(state)
    except (FileNotFoundError, json.JSONDecodeError):
        pass

    cache_state = repo_cache.state

    if cache_state.should_check_format("shards"):
        # look for shards index
        shards_data = None
        shards_index_url = f"{sd.url_w_subdir}/{REPODATA_SHARDS_FN}"

        if not repo_cache.cache_path_shards.exists():
            # avoid 304 not modified if we don't have the file
            cache_state.etag = ""
            cache_state.mod = ""
        elif not repo_cache.stale():
            # load from cache without network request
            with repo_cache.lock("r+"):
                shards_data = repo_cache.cache_path_shards.read_bytes()

        # If we don't have shards_data yet, try fetching (repodata_shards handles offline mode)
        if shards_data is None:
            try:
                shards_data = _repodata_shards(shards_index_url, repo_cache)
                cache_state.set_has_format("shards", True)
                # this will also set state["refresh_ns"] = time.time_ns(); we could
                # call cache.refresh() if we got a 304 instead:
                repo_cache.save(shards_data)
            except conda.gateways.repodata.UnavailableInvalidChannel as err:
                # repodata_shards converts HTTP errors to conda errors.
                # fetch repodata.json / repodata.json.zst instead
                if _is_http_error_most_400_codes(err.status_code):
                    cache_state.set_has_format("shards", False)
                repo_cache.refresh()
            except conda.exceptions.CondaHTTPError as err:
                # repodata_shards converts HTTP errors to conda errors.
                # fetch repodata.json / repodata.json.zst instead
                if (
                    hasattr(err._caused_by, "response")
                    and hasattr(err._caused_by.response, "status_code")
                    and _is_http_error_most_400_codes(
                        err._caused_by.response.status_code
                    )
                ):
                    cache_state.set_has_format("shards", False)
                repo_cache.refresh()

        if shards_data:
            # basic parse (move into caller?)
            shards_index: ShardsIndexDict = msgpack.loads(
                capped_decompress(shards_data, max_output_size=ZSTD_MAX_SHARD_SIZE)
            )  # type: ignore
            shards = Shards(shards_index, shards_index_url)
            return shards

    return None


def batch_retrieve_from_cache(
    shardlikes: Sequence[ShardBase], packages: list[str], shard_cache: cache.ShardCache
) -> list[ShardFetch]:
    """
    Given a list of ShardBase objects and a list of package names, fetch all URLs
    from a shared local cache, and update shardlikes with those per-package shards.
    Return ShardFetch objects for items not found in cache (to be fetched from network).
    """
    sharded = [shardlike for shardlike in shardlikes if isinstance(shardlike, Shards)]

    wanted = []
    for shardlike in sharded:
        for package_name in packages:
            if package_name in shardlike:  # and not package_name in shardlike.visited
                wanted.append(
                    (
                        shardlike,
                        package_name,
                        shardlike.shard_url(package_name),
                    )
                )

    log.debug("%d shards to fetch", len(wanted))

    if not sharded:
        log.debug("No sharded channels found.")
        # Return ShardFetch objects for all shardlikes (including non-Shards)
        result = []
        for shardlike in shardlikes:
            for package_name in packages:
                if package_name in shardlike:
                    result.append(ShardFetch(shardlike, package_name, shard_cache))
        return result

    from_cache = shard_cache.retrieve_multiple([shard_url for *_, shard_url in wanted])

    # add fetched Shard objects to Shards objects visited dict
    needs_network = []
    for shardlike, package, shard_url in wanted:
        if from_cache_shard := from_cache.get(shard_url):
            shardlike.visit_shard(package, from_cache_shard)
        else:
            needs_network.append(ShardFetch(shardlike, package, shard_cache))

    return needs_network


def batch_retrieve_from_network(wanted: list[ShardFetch]):
    """
    Fetch all shards in the wanted list from the network.

    Coordinate batch fetching across multiple ShardBase instances.
    """
    ShardFetch.fetch_batch(wanted)


def fetch_channels(url_to_channel: dict[str, Channel]) -> dict[str, ShardBase] | None:
    """
    Args:
        url_to_channel: not modified, must already be expanded to subdirs.

    Attempt to fetch the sharded index first and then fall back to retrieving a
    monolithic `repodata.json` file.

    Returns:
        A dict mapping channel URLs to `Shard` or `ShardLike` objects. None if
        no channels have shards. This dict preserves the key order of the input
        `url_to_channel`.
    """
    # copy incoming dict to retain order:
    channel_data: dict[str, ShardBase | None] = {url: None for url in url_to_channel}

    non_sharded_channels = []

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=_shards_connections()
    ) as executor:
        futures = {
            executor.submit(
                fetch_shards_index, SubdirData(Channel(channel_url))
            ): channel_url
            for (channel_url, _) in url_to_channel.items()
        }
        futures_non_sharded = {}

        for future in concurrent.futures.as_completed(futures):
            channel_url = futures[future]
            found = future.result()
            if found:
                channel_data[channel_url] = found
            else:
                non_sharded_channels.append((channel_url, Channel(channel_url)))

        # If all are None then don't do ShardLike.
        if all(value is None for value in channel_data.values()):
            return None  # caller should interpret this as falling back to the older code path

        # Latency penalty launching these requests here instead of when we
        # non_sharded_channels.append(), but we want to leave a fallback to the
        # non-sharded path open.
        for channel_url, _ in non_sharded_channels:
            futures_non_sharded[
                executor.submit(
                    SubdirData(Channel(channel_url)).repo_fetch.fetch_latest_parsed
                )
            ] = channel_url

        for future in concurrent.futures.as_completed(futures_non_sharded):
            channel_url = futures_non_sharded[future]
            repodata_json, _ = future.result()
            # the filename is not strictly repodata.json since we could have
            # fetched the same data from repodata.json.zst; but makes the
            # urljoin consistent with shards which end with
            # /repodata_shards.msgpack.zst
            url = f"{channel_url}/repodata.json"
            found = ShardLike(repodata_json, url)
            channel_data[channel_url] = found

    return {url: shard for url, shard in channel_data.items() if shard is not None}
