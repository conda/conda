# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Synchronous fetch API for sharded repodata.

This module provides unified I/O operations for fetching shards from both
ShardLike (monolithic repodata) and Shards (true sharded repodata) sources.

Key responsibilities:
1. ShardFetch - Stateful wrapper managing fetch operations per ShardBase
2. batch_retrieve_from_cache() - Fetch multiple shards from local cache
3. batch_retrieve_from_network() - Fetch multiple shards from network
4. Network I/O, decompression, and cache management

The design separates concerns:
- ShardBase/ShardLike/Shards: data structures, no fetch implementations
- ShardFetch: unified fetch API, manages I/O state
- Traversal algorithms: pure graph algorithms, delegate fetch to ShardFetch
"""

from __future__ import annotations

import logging
import sys
from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .misc import filter_redundant_packages
from .shards import shard_mentioned_packages

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

    from .cache import ShardCache
    from .shards import ShardBase, Shards
    from .subset import RepodataSubset
    from .typing import ShardDict

log = logging.getLogger(__name__)

# For reference, the largest shard "conda-forge/linux-64/vim" is 2608283 bytes
# or < 2**19*5 decompressed (486155 bytes compressed); the index is 575219 bytes
# decompressed (514039 bytes compressed) and is mostly uncompressible hash data.
ZSTD_MAX_SHARD_SIZE = 2**20 * 16


# Node and NodeId moved here from subset.py to avoid circular imports
# These are used by neighbors() and outgoing() functions which are now in sync.py
@dataclass(order=True)
class Node:
    distance: int = sys.maxsize
    package: str = ""
    channel: str = ""
    visited: bool = False
    shard_url: str = ""

    def to_id(self) -> NodeId:
        return NodeId(self.package, self.channel, self.shard_url)


@dataclass(order=True, eq=True, frozen=True)
class NodeId:
    package: str
    channel: str
    shard_url: str = ""

    def __hash__(self):
        return hash((self.package, self.channel, self.shard_url))


class ShardFetch:
    """
    Stateful wrapper around a ShardBase object for synchronous shard fetching.

    This class encapsulates all I/O operations (network fetch, decompression, caching)
    required to fetch shards. It provides a unified interface that works with both
    ShardLike (in-memory dict access) and Shards (network I/O with caching).

    Responsibilities:
    - Manage fetch state and logging
    - Coordinate network requests and cache operations
    - Handle decompression and data processing
    - Update visited cache after successful fetch
    - Own the ShardCache instance for the entire traversal

    Usage:
        ```python
        # Create fetcher with owned cache for persistent use during traversal
        fetcher = ShardFetch(shardlike, cache=shard_cache)

        # Single fetch
        shard = fetcher.fetch_shard("python")
        fetcher.visit_shard("python", shard)

        # Batch fetch
        shards = fetcher.fetch_shards(["python", "numpy", "pandas"])
        for package, shard in shards.items():
            fetcher.visit_shard(package, shard)
        ```
    """

    def __init__(self, shardlike: ShardBase, cache: ShardCache | None = None):
        """
        Initialize ShardFetch with a ShardBase object and optional cache.

        Args:
            shardlike: A ShardBase instance (either Shards or ShardLike)
            cache: Optional ShardCache instance. If provided, will be used for caching.
                   For Shards objects, this cache is used for persistent caching.
        """
        self.shardlike = shardlike
        self.cache = cache

        # If cache is provided and this is a Shards object, inject the cache
        if cache is not None and hasattr(shardlike, "shards_cache"):
            shardlike.shards_cache = cache

        log.debug(
            "ShardFetch initialized for %s (cache=%s)",
            self.shardlike.url,
            "owned" if cache else "none",
        )

    def fetch_shard(self, package: str) -> ShardDict:
        """
        Fetch a single shard for the given package.

        For ShardLike: returns package dict from in-memory repodata
        For Shards: fetches from network/cache, decompresses, updates cache

        Args:
            package: Package name to fetch

        Returns:
            ShardDict containing packages and packages.conda for this package

        Raises:
            KeyError: if package is not in the shard index
        """
        log.debug("Fetching shard for package: %s", package)
        shard = self.fetch_shards([package])[package]
        log.debug("Successfully fetched shard for package: %s", package)
        return shard

    def fetch_shards(self, packages: Iterable[str]) -> dict[str, ShardDict]:
        """
        Fetch multiple shards in one operation.

        For ShardLike: returns package dicts from in-memory repodata
        For Shards: batches network requests using ThreadPoolExecutor for efficiency

        Args:
            packages: Iterable of package names to fetch

        Returns:
            Dictionary mapping package names to their ShardDicts

        Raises:
            KeyError: if any package is not in the shard index
        """
        packages_list = list(packages)
        log.debug("Fetching %d shards", len(packages_list))

        # Delegate to implementation-specific fetch logic
        if hasattr(self.shardlike, "_fetch_shards_impl"):
            # Shards implementation
            shards = self.shardlike._fetch_shards_impl(packages_list)
        else:
            # ShardLike implementation (simple dict access)
            shards = {
                package: self.shardlike.shards[package] for package in packages_list
            }

        log.debug("Successfully fetched %d shards", len(shards))
        return shards

    def visit_package(self, package: str) -> ShardDict:
        """
        Return a shard that is already loaded and mark as visited.

        This is used when the shard is known to be in memory (e.g., from ShardLike).

        Args:
            package: Package name

        Returns:
            ShardDict for the package

        Raises:
            KeyError: if package is not already visited/in memory
        """
        log.debug("Visiting cached shard for package: %s", package)
        return self.shardlike.visit_package(package)

    def visit_shard(self, package: str, shard: ShardDict):
        """
        Store a shard in the visited cache.

        Args:
            package: Package name
            shard: ShardDict to store
        """
        log.debug("Storing visited shard for package: %s", package)
        self.shardlike.visit_shard(package, shard)

    def __repr__(self) -> str:
        return f"ShardFetch({self.shardlike!r})"


def batch_retrieve_from_cache(sharded: list[Shards], packages: list[str]):
    """
    Fetch multiple shards from local SQLite cache.

    Given a list of Shards objects and package names, attempt to retrieve all
    shards from the shared local cache. Updates Shards.visited dict for found
    shards. Returns list of (Shards, package, URL) tuples that must be fetched
    from the network.

    Args:
        sharded: List of Shards objects (ShardLike objects are filtered out)
        packages: List of package names to fetch

    Returns:
        List of (Shards, package name, shard URL) tuples for network fetching
    """
    # Filter to Shards only (ShardLike has no cache)
    sharded = [shardlike for shardlike in sharded if hasattr(shardlike, "shards_cache")]

    wanted = []
    # Build list of (shard, package, URL) tuples we need
    for shard in sharded:
        for package_name in packages:
            if package_name in shard:  # Check if package in shard index
                wanted.append((shard, package_name, shard.shard_url(package_name)))

    log.debug("Attempting to retrieve %d shards from cache", len(wanted))

    if not sharded:
        log.debug("No sharded channels found.")
        return wanted

    # All Shards share the same cache (from _install_shards_cache context manager)
    shared_shard_cache = sharded[0].shards_cache
    if not shared_shard_cache:
        log.debug("No shared cache available, will fetch from network")
        return wanted

    from_cache = shared_shard_cache.retrieve_multiple(
        [shard_url for *_, shard_url in wanted]
    )

    # Mark retrieved shards as visited
    network_needed = []
    for shard, package, shard_url in wanted:
        if from_cache_shard := from_cache.get(shard_url):
            log.debug("Retrieved %s from cache", package)
            shard.visit_shard(package, from_cache_shard)
        else:
            network_needed.append((shard, package, shard_url))

    log.debug(
        "Cache retrieved %d shards, %d need network fetch",
        len(wanted) - len(network_needed),
        len(network_needed),
    )

    return network_needed


def batch_retrieve_from_network(wanted: list[tuple[Shards, str, str]]):
    """
    Fetch multiple shards from network using _fetch_shards_impl.

    Given a list of (Shards, package name, shard URL) tuples, groups by Shards
    object and calls _fetch_shards_impl with all packages for that Shards.

    Args:
        wanted: List of (Shards, package name, shard URL) tuples from batch_retrieve_from_cache
    """
    shard_packages: dict[Shards, list[str]] = defaultdict(list)
    for shard, package, _ in wanted:
        shard_packages[shard].append(package)

    log.debug(
        "Fetching %d shards from network across %d channels",
        len(wanted),
        len(shard_packages),
    )

    for shard, packages in shard_packages.items():
        log.debug("Fetching %d shards from %s", len(packages), shard.url)
        shard._fetch_shards_impl(packages)


def neighbors(self: RepodataSubset, node: Node) -> Iterator[Node]:
    """
    Retrieve all unvisited neighbors of a node

    Neighbors in the context are dependencies of a package
    """
    discovered = set()

    for shardlike in self.shardlikes:
        if node.package not in shardlike:
            continue

        # Get the fetcher for this shardlike (created during traversal setup)
        # ShardFetch owns the cache instance shared across all shardlikes
        fetcher = self.fetchers.get(shardlike) or ShardFetch(shardlike)
        shard = fetcher.fetch_shard(node.package)

        shard = filter_redundant_packages(shard, self._use_only_tar_bz2)
        fetcher.visit_shard(node.package, shard)

        for package in shard_mentioned_packages(shard):
            node_id = NodeId(package, shardlike.url)

            if node_id not in self.nodes:
                self.nodes[node_id] = Node(node.distance + 1, package, shardlike.url)
                yield self.nodes[node_id]

                if package not in discovered:
                    # now this is per package name, not per (name, channel) tuple
                    discovered.add(package)


def outgoing(self: RepodataSubset, node: Node):
    """
    All nodes that can be reached by this node, plus cost.
    """
    # If we set a greater cost for sharded repodata than the repodata that
    # is already in memory and tracked nodes as (channel, package) tuples,
    # we might be able to find more shards-to-fetch-in-parallel more
    # quickly. On the other hand our goal is that the big channels will all
    # be sharded.
    for n in self.neighbors(node):
        yield n, 1
