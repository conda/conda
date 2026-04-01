# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (C) 2022 Anaconda, Inc
# Copyright (C) 2023 conda
# SPDX-License-Identifier: BSD-3-Clause
"""
Models for sharded repodata, and to make monolithic repodata look like sharded
repodata.
"""

from __future__ import annotations

import abc
import concurrent.futures
import logging
from collections import defaultdict
from typing import TYPE_CHECKING
from urllib.parse import urljoin, urlparse, urlunparse, uses_relative

import msgpack
import zstandard

import conda.exceptions
import conda.gateways.repodata
from conda.base.context import context
from conda.common.serialize.json import JSONDecodeError
from conda.common.serialize.json import loads as json_loads
from conda.core.subdir_data import SubdirData
from conda.gateways.connection.session import get_session
from conda.gateways.repodata import (
    _add_http_value_to_dict,
    conda_http_errors,
)
from conda.models.channel import Channel
from conda.models.match_spec import MatchSpec

from .cache import AnnotatedRawShard

log = logging.getLogger(__name__)

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, KeysView

    from requests import Response

    from conda.gateways.repodata import RepodataCache

    from .cache import ShardCache
    from .typing import PackageRecordDict, RepodataDict, ShardDict, ShardsIndexDict

SHARDS_CONNECTIONS_DEFAULT = 10
ZSTD_MAX_SHARD_SIZE = (
    2**20 * 16
)  # maximum size necessary when compressed data has no size header

# Schemes that urljoin handles correctly (registered in urllib.parse.uses_relative)
_URLJOIN_SAFE_SCHEMES = frozenset(uses_relative)


def _safe_urljoin_with_slash(base_url: str, relative_url: str = "") -> str:
    """
    Join base_url with relative_url, ensuring proper handling of all URL schemes.

    Python's urllib.parse.urljoin only handles schemes registered in
    ``urllib.parse.uses_relative``. For unregistered schemes like ``s3://``,
    it returns just ``"."`` instead of the resolved URL. This function falls
    back to a scheme-swap workaround for those cases.

    The result always ends with "/" to enable proper string concatenation with filenames.

    See: https://github.com/conda/conda-libmamba-solver/issues/866
    """
    parsed = urlparse(base_url)

    # For schemes that urljoin handles correctly, use the standard behavior
    if parsed.scheme in _URLJOIN_SAFE_SCHEMES:
        # Standard urljoin behavior: join with relative_url, then "." for trailing slash
        result = urljoin(urljoin(base_url, relative_url), ".")
        return result

    # For unregistered schemes (e.g. s3://), urljoin drops the host.
    # Work around that by temporarily swapping in https://, then restoring
    # the original scheme on the result.
    relative_parsed = urlparse(relative_url)
    if not relative_parsed.scheme and parsed.scheme:
        https_base_url = urlunparse(parsed._replace(scheme="https"))
        joined_https = urljoin(urljoin(https_base_url, relative_url), ".")
        result = urlunparse(urlparse(joined_https)._replace(scheme=parsed.scheme))
    else:
        result = urljoin(urljoin(base_url, relative_url), ".")

    # Ensure trailing slash for proper concatenation
    if not result.endswith("/"):
        result += "/"

    return result


def _shards_connections() -> int:
    """
    If context.repodata_threads is not set, find the size of the connection pool
    in a typical https:// session. This should significantly reduce dropped
    connections. We match requests' default 10.

    Is this shared between all sessions? Or do we get a different pool for a
    different get_session(url)?

    Other adapters (file://, s3://) used in conda would have different
    concurrency behavior;  we are not prepared to have separate threadpools per
    connection type.
    """
    if context.repodata_threads is not None:
        return context.repodata_threads
    return SHARDS_CONNECTIONS_DEFAULT


def default_parse_dep_name(spec: str) -> str:
    """
    Given a dependency spec string from repodata, return the package name using
    conda's MatchSpec parser.
    """
    # Note: hope for no MatchSpec-without-name in repodata, although it is
    # possible in the MatchSpec grammar.
    return MatchSpec(spec).name


def ensure_hex_hash(record: PackageRecordDict):
    """
    Convert bytes checksums to hex; leave unchanged if already str.
    """
    for hash_type in "sha256", "md5":
        if hash_value := record.get(hash_type):
            if not isinstance(hash_value, str):
                record[hash_type] = bytes(hash_value).hex()
    return record


def shard_mentioned_packages(
    shard: ShardDict,
    parse_dep_name: Callable[[str], str] | None = None,
) -> Iterable[str]:
    """
    Return all dependency names mentioned in a shard, not including the shard's
    own package name.

    parse_dep_name:
        Callable mapping a dependency string to a package name. Defaults to
        :func:`default_parse_dep_name` (conda MatchSpec). Solvers may pass a
        different parser for parity with their backend.
    """
    _parse = parse_dep_name or default_parse_dep_name
    unique_specs = set()
    for package in (*shard["packages"].values(), *shard["packages.conda"].values()):
        ensure_hex_hash(package)  # otherwise we could do this at serialization
        for spec in (
            *package.get("depends", ()),
        ):  # , *package.get("constrains", ())):
            if spec in unique_specs:
                continue
            unique_specs.add(spec)
            name = _parse(spec)
            yield name  # not much improvement from only yielding unique names


class ShardBase(abc.ABC):
    """
    Abstract base class for shard-like objects.

    Defines the common interface for both sharded repodata (Shards)
    and traditional repodata presented as shards (ShardLike).
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

    @abc.abstractmethod
    def fetch_shard(self, package: str) -> ShardDict:
        """
        Fetch an individual shard for the given package.
        """
        ...

    @abc.abstractmethod
    def fetch_shards(self, packages: Iterable[str]) -> dict[str, ShardDict]:
        """
        Fetch multiple shards in one go.
        """
        ...

    def build_repodata(self) -> RepodataDict:
        """
        Return monolithic repodata including all visited shards.
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
                    f'repodata["info"]["base_url"] was not a str, got {type(base_url)}'
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
        shard = self.fetch_shard(package)
        if shard is None:
            raise RuntimeError(f"fetch_shard({package!r}) returned None")
        return shard

    def fetch_shard(self, package: str) -> ShardDict:
        """
        "Fetch" an individual shard.

        Update self.visited with all not-None packages.

        Raise KeyError if package is not in the index.
        """
        shard = self.shards[package]
        self.visited[package] = shard
        return shard

    def fetch_shards(self, packages: Iterable[str]) -> dict[str, ShardDict]:
        """
        Fetch multiple shards in one go.

        Update self.visited with all not-None packages.
        """
        return {package: self.fetch_shard(package) for package in packages}


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
    shards_cache: ShardCache | None

    def __init__(
        self, shards_index: ShardsIndexDict, url: str, cache: ShardCache | None = None
    ):
        """
        Args:
            shards_index: raw parsed msgpack dict. Don't change it or base_url,
            shards_base_url will be wrong.
            url: URL of repodata_shards.msgpack.zst
        """
        self.shards_index = shards_index
        self.url = url
        self.shards_cache = cache

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
        shard_name = f"{bytes(self.packages_index[package]).hex()}.msgpack.zst"
        # "Individual shards are stored under the URL <shards_base_url><sha256>.msgpack.zst"
        return f"{self.shards_base_url}{shard_name}"

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

    def fetch_shard(self, package: str) -> ShardDict:
        """
        Fetch an individual shard for the given package.

        Default implementation calls fetch_shards() with a single package.
        Subclasses may override for more efficient single-fetch operations.

        Raise KeyError if package is not in the index.
        """
        return self.fetch_shards([package])[package]

    def fetch_shards(self, packages: Iterable[str]) -> dict[str, ShardDict]:
        """
        Return mapping of *package names* to Shard for given packages.

        If a shard is already in self.visited, it is not fetched again.
        """
        results = {}

        def fetch(s, url, package_to_fetch):
            response = s.get(url)
            response.raise_for_status()
            data = response.content

            return AnnotatedRawShard(
                url=url, package=package_to_fetch, compressed_shard=data
            )

        packages = sorted(list(packages))
        urls_packages = {}  # package shards to fetch
        for package in packages:
            if package in self.visited:
                results[package] = self.visited[package]
            else:
                urls_packages[self.shard_url(package)] = package

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=_shards_connections()
        ) as executor:
            futures = {
                executor.submit(fetch, self.session, url, package): (url, package)
                for url, package in urls_packages.items()
                if package not in results
            }
            for future in concurrent.futures.as_completed(futures):
                log.debug(". %s", futures[future])
                url, package = futures[future]
                self._process_fetch_result(future, url, package, results)

        self.visited.update(results)

        return results

    def _process_fetch_result(self, future, url, package, results):
        """
        Process a single fetched shard.
        """
        # Fail early if no cache to store the result.
        if self.shards_cache is None:
            raise ValueError("self.shards_cache is None")

        with conda_http_errors(url, package):
            fetch_result = future.result()

        # Decompress and save record
        results[fetch_result.package] = msgpack.loads(
            zstandard.decompress(
                fetch_result.compressed_shard, max_output_size=ZSTD_MAX_SHARD_SIZE
            )
        )
        self.shards_cache.insert(fetch_result)


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
    filename = "repodata_shards.msgpack.zst"

    with conda_http_errors(url, filename):
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
def _is_http_error_most_400_codes(status_code: str | int) -> bool:
    """
    Determine whether the `HTTPError` is an HTTP 400 error code (except for 416).
    """
    return (
        isinstance(status_code, int) and 400 <= status_code < 500 and status_code != 416
    )


def fetch_shards_index(sd: SubdirData, cache: ShardCache | None) -> Shards | None:
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

    # Load state ourselves to avoid clearing when binary cached data is missing.
    # If we fall back to monolithic repodata.json, the standard fetch code will
    # load the state again in text mode.
    try:
        with repo_cache.lock("r+") as state_file:
            # cannot use pathlib.read_text / write_text on any locked file, as
            # it will release the lock early
            state = json_loads(state_file.read())
            repo_cache.state.update(state)
    except (FileNotFoundError, JSONDecodeError):
        pass

    cache_state = repo_cache.state

    if cache_state.should_check_format("shards"):
        # look for shards index
        shards_data = None
        shards_index_url = f"{sd.url_w_subdir}/repodata_shards.msgpack.zst"

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
                zstandard.decompress(shards_data, max_output_size=ZSTD_MAX_SHARD_SIZE)
            )  # type: ignore
            shards = Shards(shards_index, shards_index_url, cache)
            return shards

    return None


def batch_retrieve_from_cache(sharded: list[Shards], packages: list[str]):
    """
    Given a list of Shards objects and a list of package names, fetch all URLs
    from a shared local cache, and update Shards with those per-package shards.
    Return the remaining URLs that must be fetched from the network.
    """
    sharded = [shardlike for shardlike in sharded if isinstance(shardlike, Shards)]

    wanted = []
    # XXX update batch_retrieve_from_cache to work with (Shards, package name)
    # tuples instead of broadcasting across shards itself.
    for shard in sharded:
        for package_name in packages:
            if package_name in shard:  # and not package_name in shard.visited
                wanted.append((shard, package_name, shard.shard_url(package_name)))

    log.debug("%d shards to fetch", len(wanted))

    if not sharded:
        log.debug("No sharded channels found.")
        return wanted

    shared_shard_cache = sharded[0].shards_cache
    from_cache = shared_shard_cache.retrieve_multiple(
        [shard_url for *_, shard_url in wanted]
    )

    # add fetched Shard objects to Shards objects visited dict
    for shard, package, shard_url in wanted:
        if from_cache_shard := from_cache.get(shard_url):
            shard.visit_shard(package, from_cache_shard)

    return wanted


def batch_retrieve_from_network(wanted: list[tuple[Shards, str, str]]):
    """
    Given a list of (Shards, package name, shard URL) tuples, group by Shards and call fetch_shards
    with a list of all URLs for that Shard.
    """
    shard_packages: dict[Shards, list[str]] = defaultdict(list)
    for shard, package, _ in wanted:
        shard_packages[shard].append(package)

    # XXX it might be better to pull networking and Session() out of Shards(),
    # so that we can e.g. use the same session for a Channel(); typically a
    # noarch+arch pair of subdirs.
    # Could we share a ThreadPoolExecutor and see better session utilization?
    for shard, packages in shard_packages.items():
        shard.fetch_shards(packages)


def fetch_channels(url_to_channel: dict[str, Channel]) -> dict[str, ShardBase] | None:
    """
    Args:
        url_to_channel: not modified, must already be expanded to subdirs.

    Attempt to fetch the sharded index first and then fall back to retrieving a
    traditional `repodata.json` file.

    Returns:
        A dict mapping channel URLs to `Shard` or `ShardLike` objects. None if
        no channels have shards. This dict preserves the key order of the input
        `url_to_channel`.
    """
    # copy incoming dict to retain order:
    channel_data: dict[str, ShardBase | None] = {url: None for url in url_to_channel}

    # The parallel version may reorder channels, does this matter?

    non_sharded_channels = []

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=_shards_connections()
    ) as executor:
        futures = {
            executor.submit(
                fetch_shards_index, SubdirData(Channel(channel_url)), None
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
