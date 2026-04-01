# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (C) 2022 Anaconda, Inc
# Copyright (C) 2023 conda
# SPDX-License-Identifier: BSD-3-Clause
"""
Sharded repodata subsets.

Traverse dependencies of installed and to-be-installed packages to generate a
useful subset for the solver.

The algorithm developed here is a direct result of the following CEP:

- https://conda.org/learn/ceps/cep-0016 (Sharded Repodata)
"""

from __future__ import annotations

import functools
import logging
import queue
import sys
import threading
from collections import deque
from concurrent.futures import Future, ThreadPoolExecutor
from contextlib import contextmanager, suppress
from dataclasses import dataclass
from pathlib import Path
from queue import SimpleQueue
from typing import TYPE_CHECKING, TypeVar

import msgpack
import zstandard

import conda.gateways.repodata
from conda.base.context import context

from .cache import AnnotatedRawShard, ShardCache
from .core import (
    ZSTD_MAX_SHARD_SIZE,
    Shards,
    _shards_connections,
    batch_retrieve_from_cache,
    batch_retrieve_from_network,
    default_parse_dep_name,
    fetch_channels,
    shard_mentioned_packages,
)

log = logging.getLogger(__name__)

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Iterator, Sequence
    from queue import SimpleQueue as Queue
    from typing import Literal

    from conda.models.channel import Channel

    from .core import ShardBase
    from .typing import ShardDict

# Waiting for worker threads to shutdown cleanly, or raise error.
THREAD_WAIT_TIMEOUT = 5  # seconds
REACHABLE_PIPELINED_MAX_TIMEOUTS = (
    10  # number of times we can timeout waiting for shards
)


@dataclass(order=True)
class Node:
    distance: int = sys.maxsize
    package: str = ""
    channel: str = ""
    visited: bool = False
    shard_url: str = ""

    def to_id(self) -> NodeId:
        return NodeId(self.package, self.channel, shard_url=self.shard_url)


@dataclass(order=True, eq=True, frozen=True)
class NodeId:
    package: str
    channel: str
    shard_url: str = ""

    def __hash__(self):
        return hash((self.package, self.channel, self.shard_url))


def _nodes_from_packages(
    root_packages: list[str], shardlikes: Iterable[ShardBase]
) -> Iterator[tuple[NodeId, Node]]:
    """
    Yield (NodeId, Node) for all root packages found in shardlikes.
    """
    for package in root_packages:
        for shardlike in shardlikes:
            if package in shardlike:
                node = Node(
                    0, package, shardlike.url, shard_url=shardlike.shard_url(package)
                )
                node_id = node.to_id()
                yield node_id, node


def filter_redundant_packages(repodata: ShardDict, use_only_tar_bz2=False) -> ShardDict:
    """
    Given repodata or a single shard, remove any .tar.bz2 packages that have a
    .conda counterpart.

    Return a shallow copy if use_only_tar_bz2==False, else unmodified input.
    """
    if use_only_tar_bz2:
        return repodata

    _tar_bz2 = ".tar.bz2"
    _conda = ".conda"
    _len_tar_bz2 = len(_tar_bz2)

    legacy_packages = repodata.get("packages", {})
    conda_packages = repodata.get("packages.conda", {})

    return {
        **repodata,
        "packages": {
            k: v
            for k, v in legacy_packages.items()
            if f"{k[:-_len_tar_bz2]}{_conda}" not in conda_packages
        },
    }


@contextmanager
def _install_shards_cache(shardlikes):
    """
    Add shards_cache to shardlikes for duration of traversal, then remove and
    close.
    """
    with ShardCache(Path(conda.gateways.repodata.create_cache_dir())) as cache:
        for shardlike in shardlikes:
            if isinstance(shardlike, Shards):
                shardlike.shards_cache = cache
        yield cache
        for shardlike in shardlikes:
            if isinstance(shardlike, Shards):
                shardlike.shards_cache = None


@dataclass
class RepodataSubset:
    nodes: dict[NodeId, Node]
    shardlikes: Sequence[ShardBase]
    DEFAULT_STRATEGY = "pipelined"

    def __init__(
        self,
        shardlikes: Iterable[ShardBase],
        parse_dep_name: Callable[[str], str] | None = None,
    ):
        self.nodes = {}
        self.shardlikes = list(shardlikes)
        self._use_only_tar_bz2 = context.use_only_tar_bz2
        self._parse_dep_name = parse_dep_name or default_parse_dep_name

    @classmethod
    def has_strategy(cls, strategy: str) -> bool:
        """
        Return True if this class provides the named shard traversal strategy.
        """
        return hasattr(cls, f"reachable_{strategy}")

    def neighbors(self, node: Node) -> Iterator[Node]:
        """
        Retrieve all unvisited neighbors of a node

        Neighbors in the context are dependencies of a package
        """
        discovered = set()

        for shardlike in self.shardlikes:
            if node.package not in shardlike:
                continue

            # check that we don't fetch the same shard twice...
            shard = shardlike.fetch_shard(
                node.package
            )  # XXX this is the only place that in-memory (repodata.json) shards are found for the first time

            shard = filter_redundant_packages(shard, self._use_only_tar_bz2)
            shardlike.visit_shard(node.package, shard)

            for package in shard_mentioned_packages(shard, self._parse_dep_name):
                node_id = NodeId(package, shardlike.url)

                if node_id not in self.nodes:
                    self.nodes[node_id] = Node(
                        node.distance + 1, package, shardlike.url
                    )
                    yield self.nodes[node_id]

                    if package not in discovered:
                        # now this is per package name, not per (name, channel) tuple
                        discovered.add(package)

    def outgoing(self, node: Node):
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

    def reachable(self, root_packages, *, strategy=DEFAULT_STRATEGY) -> None:
        """
        Run named reachability strategy or the default.

        Update `self.shardlikes` with reachable package records. Later,
        [shardlike.build_repodata() for shardlike in shardlikes] can be used to
        generate repodata.json-format subsets of each channel.
        """
        return getattr(self, f"reachable_{strategy}")(root_packages)

    def reachable_bfs(self, root_packages):
        """
        Fetch all packages reachable from `root_packages`' by following
        dependencies using the "breadth-first search" algorithm.

        Update associated `self.shardlikes` to contain enough data to build a
        repodata subset.
        """
        with _install_shards_cache(self.shardlikes):
            return self._reachable_bfs(root_packages)

    def _reachable_bfs(self, root_packages):
        """
        Inner reachable_bfs() implementation.
        """
        self.nodes = dict(_nodes_from_packages(root_packages, self.shardlikes))

        node_queue = deque(self.nodes.values())
        sharded = [s for s in self.shardlikes if isinstance(s, Shards)]

        while node_queue:
            # Batch fetch all nodes at current level
            to_retrieve = {node.package for node in node_queue if not node.visited}
            if to_retrieve:
                not_in_cache = batch_retrieve_from_cache(sharded, sorted(to_retrieve))
                batch_retrieve_from_network(not_in_cache)

            # Process one level
            level_size = len(node_queue)
            for _ in range(level_size):
                node = node_queue.popleft()
                if node.visited:  # pragma: no cover
                    continue  # we should never add visited nodes to node_queue
                node.visited = True

                for next_node, _ in self.outgoing(node):
                    if not next_node.visited:
                        node_queue.append(next_node)

    def reachable_pipelined(self, root_packages):
        """
        Fetch all packages reachable from `root_packages`' by following
        dependencies.

        Build repodata subset using concurrent threads to follow dependencies,
        fetch from cache, and fetch from network.
        """

        # In offline mode shards are retrieved from the cache database as usual,
        # but cache misses are forwarded to offline_nofetch_thread returning
        # empty shards.
        if context.offline:
            network_worker = offline_nofetch_thread
        else:
            network_worker = network_fetch_thread

        # Ignore cache on shards object, use our own. Necessary if there are no
        # sharded channels.
        with ShardCache(Path(conda.gateways.repodata.create_cache_dir())) as cache:
            return self._reachable_pipelined(
                root_packages, network_worker=network_worker, cache=cache
            )

    def _reachable_pipelined(
        self,
        root_packages,
        network_worker: Callable[
            [
                Queue[Sequence[NodeId] | None],
                Queue[list[tuple[NodeId, ShardDict] | Exception]],
                ShardCache,
                Sequence[ShardBase],
            ],
            None,
        ],
        cache: ShardCache,
    ):
        """
        Set up queues and threads for shard traversal with a configurable
        network_worker. Called by reachable_pipelined()
        """

        cache_in_queue: SimpleQueue[list[NodeId] | None] = SimpleQueue()
        shard_out_queue: SimpleQueue[list[tuple[NodeId, ShardDict]] | Exception] = (
            SimpleQueue()
        )
        cache_miss_queue: SimpleQueue[list[NodeId] | None] = SimpleQueue()

        cache_thread = threading.Thread(
            target=cache_fetch_thread,
            args=(cache_in_queue, shard_out_queue, cache_miss_queue, cache),
            daemon=True,  # may have to set to False if we ever want to run in a subinterpreter
        )

        network_thread = threading.Thread(
            target=network_worker,
            args=(cache_miss_queue, shard_out_queue, cache, self.shardlikes),
            daemon=True,
        )

        try:
            cache_thread.start()
            network_thread.start()
            self._pipelined_traversal(
                root_packages,
                cache_in_queue,
                shard_out_queue,
                cache_thread,
                network_thread,
            )
        finally:
            cache_in_queue.put(None)
            # These should finish almost immediately, but if not, raise an error:
            cache_thread.join(THREAD_WAIT_TIMEOUT)
            network_thread.join(THREAD_WAIT_TIMEOUT)

    def _pipelined_traversal(
        self,
        root_packages,
        cache_in_queue: Queue[list[NodeId] | None],
        shard_out_queue: Queue[list[tuple[NodeId, ShardDict]] | Exception],
        cache_thread: threading.Thread,
        network_thread: threading.Thread,
    ):
        """
        Run reachability algorithm given queues to submit and receive shards.
        """
        shardlikes_by_url = {s.url: s for s in self.shardlikes}
        pending: set[NodeId] = set()
        in_flight: set[NodeId] = set()
        timeouts = 0

        self.nodes = {}

        # create start condition
        parent_node = Node(0)
        pending.update(self.visit_node(parent_node, root_packages))

        def pump():
            """
            Find shards we already have and those we need. Submit those need to
            cache_in_queue, those we have to shard_out_queue.
            """
            have, need = self.drain_pending(pending, shardlikes_by_url)
            if need:
                in_flight.update(need)
                cache_in_queue.put(need)
            if have:
                in_flight.update(node_id for node_id, _ in have)
                # All shards go through shard_out queue to be processed at
                # shard_out_queue.get(). Whether they come from cache, network,
                # or for repodata.json we "have" them (already in memory).
                shard_out_queue.put(have)
            return len(have) + len(need)

        def log_timeout():
            """
            Log timeout information and raise TimeoutError if max timeouts
            exceeded.
            """
            nonlocal timeouts
            timeouts += 1
            log.debug("Shard timeout %s", timeouts)
            log.debug(
                "in_flight: %s...", sorted(str(node_id) for node_id in in_flight)[:10]
            )
            log.debug("nodes: %d", len(self.nodes))
            log.debug("cache_thread.is_alive(): %s", cache_thread.is_alive())
            log.debug("network_thread.is_alive(): %s", network_thread.is_alive())
            log.debug("shard_out_queue.qsize(): %s", shard_out_queue.qsize())
            if timeouts > REACHABLE_PIPELINED_MAX_TIMEOUTS:
                raise TimeoutError("Timeout while fetching repodata shards.")

        while True:
            pump()
            if not in_flight:  # pending is empty right after calling pump()
                log.debug("All shards have finished processing.")
                break

            try:
                new_shards = shard_out_queue.get(timeout=1)
                if isinstance(
                    new_shards, BaseException
                ):  # error propagated from worker thread
                    raise new_shards

            except queue.Empty:
                log_timeout()
                continue

            for node_id, shard in new_shards:
                in_flight.remove(node_id)

                # remove_legacy_packages if the ".conda" format is enabled /
                # conda is not in ".tar.bz2 only" mode.
                shard = filter_redundant_packages(shard, self._use_only_tar_bz2)

                # add shard to appropriate ShardLike
                parent_node = self.nodes[node_id]
                shardlike = shardlikes_by_url[node_id.channel]
                shardlike.visit_shard(node_id.package, shard)

                pending.update(
                    self.visit_node(
                        parent_node,
                        shard_mentioned_packages(shard, self._parse_dep_name),
                    )
                )

    def visit_node(
        self, parent_node: Node, mentioned_packages: Iterable[str]
    ) -> Iterable[NodeId]:
        """Broadcast mentioned packages across channels. yield pending NodeId's."""
        # NOTE we have visit for Nodes which is used in the graph traversal
        # algorithm, and a separate visit for ShardBase which means "include
        # this package in the output repodata".
        for package in mentioned_packages:
            for shardlike in self.shardlikes:
                if package in shardlike:
                    new_node_id = NodeId(
                        package, shardlike.url, shardlike.shard_url(package)
                    )
                    if new_node_id not in self.nodes:
                        new_node = Node(
                            distance=parent_node.distance + 1,
                            package=new_node_id.package,
                            channel=new_node_id.channel,
                            shard_url=new_node_id.shard_url,
                        )
                        self.nodes[new_node_id] = new_node
                        yield new_node_id

        parent_node.visited = True

    def drain_pending(
        self, pending: set[NodeId], shardlikes_by_url: dict[str, ShardBase]
    ) -> tuple[list[tuple[NodeId, ShardDict]], list[NodeId]]:
        """
        Check pending for in-memory shards.
        Clear pending.

        Return a list of shards we have and shards we need to fetch.
        """
        shards_need = []
        shards_have = []
        for node_id in pending:
            # we should already have these nodes.
            shardlike = shardlikes_by_url[node_id.channel]
            if shardlike.shard_loaded(node_id.package):  # for monolithic repodata
                shards_have.append((node_id, shardlike.visit_package(node_id.package)))
            else:
                if self.nodes[node_id].visited:  # pragma: no cover
                    log.debug("Skip visited, should not be reached")
                    continue
                shards_need.append(node_id)
        pending.clear()
        return shards_have, shards_need


def build_repodata_subset(
    root_packages: Iterable[str],
    channels: dict[str, Channel],
    algorithm: Literal["bfs", "pipelined"] = RepodataSubset.DEFAULT_STRATEGY,
    parse_dep_name: Callable[[str], str] | None = None,
) -> dict[str, ShardBase] | None:
    """
    Retrieve all necessary information to build a repodata subset.

    Params:
        root_packages: iterable of installed and requested package names
        channels: Channel objects; dict form preferred.
        algorithm: desired traversal algorithm
        parse_dep_name: maps dependency string to package name; defaults to conda MatchSpec.

    Return:
        None if there are no shards available, or a mapping of channel URL's to
        ShardBase objects where build_repodata() returns the computed subset..
    """
    channel_data = fetch_channels(channels)
    if channel_data is not None:
        subset = RepodataSubset(
            (*channel_data.values(),), parse_dep_name=parse_dep_name
        )
        subset.reachable(root_packages, strategy=algorithm)
        log.debug("%d (channel, package) nodes discovered", len(subset.nodes))

    return channel_data


# region workers

_T = TypeVar("_T")


def combine_batches_until_none(
    in_queue: Queue[Sequence[_T] | None],
) -> Iterator[Sequence[_T]]:
    """
    Combine lists from in_queue until we see None. Yield combined lists.
    """
    running = True
    while running:
        try:
            # Add timeout to prevent indefinite blocking if producer thread fails
            batch = in_queue.get(timeout=5)
            if batch is None:
                break
        except queue.Empty:
            # If we timeout, continue waiting - producer might still send data
            continue

        node_ids = list(batch)
        with suppress(queue.Empty):
            while True:  # loop exits with break or queue.Empty exception
                batch = in_queue.get_nowait()
                if batch is None:
                    # do the work but then quit
                    running = False
                    break
                else:
                    node_ids.extend(batch)
        yield node_ids


def exception_to_queue(func):
    """
    Decorator to send unhandled exceptions to the second argument out_queue.
    """

    @functools.wraps(func)
    def wrapper(in_queue, out_queue, *args, **kwargs):
        try:
            return func(in_queue, out_queue, *args, **kwargs)
        except BaseException as e:  # includes KeyboardInterrupt
            in_queue.put(None)  # tell worker that we're done
            out_queue.put(e)  # tell caller that we received an exception

    return wrapper


@exception_to_queue
def cache_fetch_thread(
    in_queue: Queue[Sequence[NodeId] | None],
    shard_out_queue: Queue[Sequence[tuple[NodeId, ShardDict] | Exception]],
    network_out_queue: Queue[Sequence[NodeId] | None],
    cache: ShardCache,
):
    """
    Fetch batches of shards from cache until in_queue sees None. Enqueue found
    shards to shard_out_queue, and not found shards to network_out_queue.

    When we see None on in_queue, send None to both out queues and exit.

    Args:
        in_queue: NodeId (URLs) to fetch.
        shard_out_queue: fetched shards sent to queue.
        network_out_queue: cache misses forwarded to queue. Same queue is
            network_fetch_thread's in_queue.
        cache: used to retrieve shards.
    """
    with cache.copy() as cache:
        for node_ids in combine_batches_until_none(in_queue):
            cached = cache.retrieve_multiple(
                [node_id.shard_url for node_id in node_ids]
            )

            # should we add this into retrieve_multiple?
            found: list[tuple[NodeId, ShardDict]] = []
            not_found: list[NodeId] = []
            for node_id in node_ids:
                if shard := cached.get(node_id.shard_url):
                    found.append((node_id, shard))
                else:
                    not_found.append(node_id)

            # Might wake up the network thread by calling it first:
            if not_found:
                network_out_queue.put(not_found)
            if found:
                shard_out_queue.put(found)

    network_out_queue.put(None)
    # no shard_out_queue.put(None); this is during mainloop shutdown.


@exception_to_queue
def network_fetch_thread(
    in_queue: Queue[Sequence[NodeId] | None],
    shard_out_queue: Queue[list[tuple[NodeId, ShardDict] | Exception]],
    cache: ShardCache,
    shardlikes: Sequence[ShardBase],
):
    """
    Fetch shards from the network that are received on in_queue, until we see
    None.

    Unhandled exceptions also go to shard_out_queue, and exit this thread.

    Args:
        in_queue: NodeId (URLs) to fetch.
        shard_out_queue: fetched shards sent to queue.
        cache: once shards are decoded they are stored in cache.
        shardlikes: list of (network-only) shard index objects.
    """
    dctx = zstandard.ZstdDecompressor(max_window_size=ZSTD_MAX_SHARD_SIZE)
    shardlikes_by_url = {s.url: s for s in shardlikes}

    def fetch(s, url: str, node_id: NodeId):
        response = s.get(url)
        response.raise_for_status()
        data = response.content
        return url, node_id, data

    def submit(node_id: NodeId):
        # this worker should only receive network node_id's:
        shardlike = shardlikes_by_url[node_id.channel]
        if not isinstance(shardlike, Shards):
            raise TypeError("network_fetch_thread got non-network shardlike")
        session = shardlike.session
        url = shardlikes_by_url[node_id.channel].shard_url(node_id.package)
        return executor.submit(fetch, session, url, node_id)

    def handle_result(future: Future):
        url, node_id, data = future.result()
        log.debug("Fetch thread got %s (%s bytes)", url, len(data))
        # Decompress and parse. If it decodes as
        # msgpack.zst, insert into cache. Then put "known
        # good" shard into out queue.
        shard: ShardDict = msgpack.loads(
            dctx.decompress(data, max_output_size=ZSTD_MAX_SHARD_SIZE)
        )  # type: ignore[assign]
        # We could send this back into the cache thread instead to
        # serialize access to sqlite3 if lock contention becomes an issue.
        cache.insert(AnnotatedRawShard(url, node_id.package, data))
        shard_out_queue.put([(node_id, shard)])

    def result_to_in_queue(future: Future):
        # Simplify waiting by putting responses back into in_queue. This
        # function is called in the ThreadPoolExecutor's thread, but we want to
        # serialize result processing in the network_fetch_thread.

        # Not in our signature; the caller doesn't need to know we are putting
        # Future in here as well.
        in_queue.put([future])  # type: ignore

    with (
        ThreadPoolExecutor(max_workers=_shards_connections()) as executor,
        cache.copy() as cache,
    ):
        for node_ids_and_results in combine_batches_until_none(in_queue):
            for node_id_or_result in node_ids_and_results:
                if isinstance(node_id_or_result, Future):
                    handle_result(node_id_or_result)
                else:
                    future = submit(node_id_or_result)
                    future.add_done_callback(result_to_in_queue)

        # TODO call executor.shutdown(cancel_futures=True) on error or otherwise
        # prevent new HTTP requests from being started e.g. "skip" flag in
        # fetch() function. Also possible to shutdown(wait=False).


@exception_to_queue
def offline_nofetch_thread(
    in_queue: Queue[Sequence[NodeId] | None],
    shard_out_queue: Queue[list[tuple[NodeId, ShardDict] | Exception]],
    cache: ShardCache,
    shardlikes: Sequence[ShardBase],
):
    """
    For offline mode, where network requests are not allowed.
    Pretend that every network request is an empty shard.
    Don't save those to the cache.

    Depending on how many shards are in sqlite3 and which packages were requested, the user may or may not get enough repodata for a solution.

    Args:
        in_queue: NodeId (URLs) to fetch.
        shard_out_queue: fetched shards sent to queue.
        cache: once shards are decoded they are stored in cache.
        shardlikes: list of (network-only) shard index objects.
    """

    for node_ids in combine_batches_until_none(in_queue):
        for node_id in node_ids:
            shard: ShardDict = {"packages": {}, "packages.conda": {}}
            shard_out_queue.put([(node_id, shard)])


# endregion
