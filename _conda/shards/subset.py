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

In this algorithm we treat a (channel, package name) as a node, its dependencies
as edges. We then traverse all edges to discover all reachable (channel, package
name) tuples. The solver should be able to find a solution with only this
subset.

This subset is overgenerous since the user is unlikely to want to install very
old packages and their dependencies. If this is too slow, we could deploy
heuristics that automatically ignore older package versions. We could also allow
the user to configure minimum versions of common packages and ignore older
versions and their dependencies, falling back to a full solve if unsatisfiable.

We treat both sharded and monolithic repodata as if they were made up of
per-package shards, computing a subset of both. This is because it is possible
for the monolithic repodata to mention packages that exist in the true sharded
repodata but would not be found by only traversing the shards.

We treat all repodata as sharded, even if no actual sharded repodata has been
found.

## Example usage

The following constructs several repodata (`noarch` and `linux-64`) from a
single channel name and a list of root packages:

``` from conda.models.channel import Channel from
_conda.shards_subset import build_repodata_subset

channel = Channel("conda-forge-sharded/linux-64") channel_data =
build_repodata_subset(["python", "pandas"], [channel.url()]) repodata = {}

for url in channel_data:
    repodata[url] = channel_data.build_repodata()

# ... this is what's fed to the solver ```

"""

from __future__ import annotations

import logging
import queue
import sys
import threading
from collections import deque
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from queue import SimpleQueue
from typing import TYPE_CHECKING

import msgpack
import zstandard

import conda.gateways.repodata
from conda.base.context import context

from . import cache
from .cache import AnnotatedRawShard
from .misc import (
    _shards_connections,
    combine_batches_until_none,
    exception_to_queue,
    filter_redundant_packages,
)
from .shards import (
    ZSTD_MAX_SHARD_SIZE,
    Shards,
    batch_retrieve_from_cache,
    batch_retrieve_from_network,
    fetch_channels,
    shard_mentioned_packages,
)

log = logging.getLogger(__name__)

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Iterator, Sequence
    from queue import SimpleQueue as Queue
    from typing import Literal, TypeVar

    from conda.models.channel import Channel

    from .cache import ShardCache
    from .shards import ShardBase
    from .typing import ShardDict

# Waiting for worker threads to shutdown cleanly, or raise error.
THREAD_WAIT_TIMEOUT = 5  # seconds
REACHABLE_PIPELINED_MAX_TIMEOUTS = (
    10  # number of times we can timeout waiting for shards
)
QUEUE_TIMEOUT = 1


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


class RepodataSubset:
    """
    Build a subset of repodata by traversing all packages that are dependencies
    and transitive dependencies of a root set of packages.
    """

    shardlikes: Sequence[ShardBase]
    DEFAULT_STRATEGY = "pipelined"

    _nodes: dict[NodeId, Node]
    _use_only_tar_bz2: bool
    _add_pip_as_python_dependency: bool

    def __init__(self, shardlikes: Iterable[ShardBase]):
        self._nodes = {}
        self.shardlikes = list(shardlikes)
        self._use_only_tar_bz2 = context.use_only_tar_bz2
        self._add_pip_as_python_dependency = context.add_pip_as_python_dependency

    @classmethod
    def has_strategy(cls, strategy: str) -> bool:
        """
        Return True if this class provides the named shard traversal strategy.
        """
        return hasattr(cls, f"reachable_{strategy}")

    def _neighbors(self, node: Node) -> Iterator[Node]:
        """
        Retrieve all unvisited neighbors of a node.

        Neighbors in the context are dependencies of a package.

        NOTE: This method assumes that the required shards have already been
        retrieved from the network via batch_retrieve_from_network() before
        neighbors() is called. It uses visit_package() to access already-loaded shards.
        """
        discovered = set()

        for shardlike in self.shardlikes:
            if node.package not in shardlike:
                continue

            # Get the shard that should already be loaded in memory.
            # For Shards, this assumes fetch_shards() was called before neighbors()
            # is called. For ShardLike, visit_package() returns the shard immediately.
            shard = shardlike.visit_package(node.package)

            shard = filter_redundant_packages(shard, self._use_only_tar_bz2)
            # Store the filtered shard so we'll see it when we call
            # build_repodata()
            shardlike.visit_shard(node.package, shard)

            # ensure solver has "pip" record if add_pip_as_python_dependency:
            extra = (
                ("pip",)
                if self._add_pip_as_python_dependency and node.package == "python"
                else ()
            )
            for package in shard_mentioned_packages(shard, extra=extra):
                node_id = NodeId(package, shardlike.url)

                if node_id not in self._nodes:
                    self._nodes[node_id] = Node(
                        node.distance + 1, package, shardlike.url
                    )
                    yield self._nodes[node_id]

                    if package not in discovered:
                        # now this is per package name, not per (name, channel) tuple
                        discovered.add(package)

    def _outgoing(self, node: Node):
        """
        All nodes that can be reached by this node, plus cost.
        """
        # If we set a greater cost for sharded repodata than the repodata that
        # is already in memory and tracked nodes as (channel, package) tuples,
        # we might be able to find more shards-to-fetch-in-parallel more
        # quickly. On the other hand our goal is that the big channels will all
        # be sharded.
        for n in self._neighbors(node):
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
        with cache.ShardCache(
            Path(conda.gateways.repodata.create_cache_dir())
        ) as shard_cache:
            return self._reachable_bfs(root_packages, shard_cache)

    def _reachable_bfs(self, root_packages, shard_cache: cache.ShardCache):
        """
        Inner reachable_bfs() implementation.
        """
        self._nodes = dict(_nodes_from_packages(root_packages, self.shardlikes))

        node_queue = deque(self._nodes.values())

        while node_queue:
            # Batch fetch all nodes at current level
            to_retrieve = {node.package for node in node_queue if not node.visited}
            if to_retrieve:
                # Fetch from cache and network, getting ShardFetch objects for network fetches
                needs_network = batch_retrieve_from_cache(
                    self.shardlikes, sorted(to_retrieve), shard_cache
                )
                if needs_network:
                    batch_retrieve_from_network(needs_network)

            # Process one level - shards are now guaranteed to be loaded
            level_size = len(node_queue)
            for _ in range(level_size):
                node = node_queue.popleft()
                if node.visited:  # pragma: no cover
                    continue  # we should never add visited nodes to node_queue
                node.visited = True

                for next_node, _ in self._outgoing(node):
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
        with cache.ShardCache(
            Path(conda.gateways.repodata.create_cache_dir())
        ) as cache_instance:
            return self._reachable_pipelined(
                root_packages, network_worker=network_worker, cache=cache_instance
            )

    def _reachable_pipelined(
        self,
        root_packages,
        network_worker: Callable[
            [
                Queue[Sequence[NodeId] | None],
                Queue[list[tuple[NodeId, ShardDict] | Exception]],
                cache.ShardCache,
                Sequence[ShardBase],
            ],
            None,
        ],
        cache: cache.ShardCache,
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
            args=(
                cache_miss_queue,
                shard_out_queue,
                QueueCache(cache_in_queue),
                self.shardlikes,
            ),
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

        self._nodes = {}

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
            log.debug("nodes: %d", len(self._nodes))
            log.debug("cache_thread.is_alive(): %s", cache_thread.is_alive())
            log.debug("network_thread.is_alive(): %s", network_thread.is_alive())
            log.debug("shard_out_queue.qsize(): %s", shard_out_queue.qsize())
            if network_thread.is_alive() and in_flight:
                max_timeouts = int(
                    context.remote_read_timeout_secs * (context.remote_max_retries + 1)
                )
            else:
                max_timeouts = REACHABLE_PIPELINED_MAX_TIMEOUTS
            if timeouts > max_timeouts:
                raise TimeoutError("Timeout while fetching repodata shards.")

        while True:
            pump()
            if not in_flight:  # pending is empty right after calling pump()
                log.debug("All shards have finished processing.")
                break

            try:
                new_shards = shard_out_queue.get(timeout=QUEUE_TIMEOUT)
                if isinstance(
                    new_shards, BaseException
                ):  # error propagated from worker thread
                    raise new_shards

            except queue.Empty:
                log_timeout()
                continue

            timeouts = 0
            for node_id, shard in new_shards:
                in_flight.remove(node_id)

                # remove_legacy_packages if the ".conda" format is enabled /
                # conda is not in ".tar.bz2 only" mode.
                shard = filter_redundant_packages(shard, self._use_only_tar_bz2)

                # add shard to appropriate ShardLike
                parent_node = self._nodes[node_id]
                shardlike = shardlikes_by_url[node_id.channel]
                shardlike.visit_shard(node_id.package, shard)

                # ensure solver has "pip" record if add_pip_as_python_dependency:
                extra = (
                    ("pip",)
                    if self._add_pip_as_python_dependency
                    and parent_node.package == "python"
                    else ()
                )
                pending.update(
                    self.visit_node(
                        parent_node, shard_mentioned_packages(shard, extra=extra)
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
                    if new_node_id not in self._nodes:
                        new_node = Node(
                            distance=parent_node.distance + 1,
                            package=new_node_id.package,
                            channel=new_node_id.channel,
                            shard_url=new_node_id.shard_url,
                        )
                        self._nodes[new_node_id] = new_node
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
                if self._nodes[node_id].visited:  # pragma: no cover
                    log.debug("Skip visited, should not be reached")
                    continue
                shards_need.append(node_id)
        pending.clear()
        return shards_have, shards_need


def build_repodata_subset(
    root_packages: Iterable[str],
    channels: dict[str, Channel],
    algorithm: Literal["bfs", "pipelined"] = RepodataSubset.DEFAULT_STRATEGY,
) -> dict[str, ShardBase] | None:
    """
    Retrieve all necessary information to build a repodata subset.

    Params:
        root_packages: iterable of installed and requested package names
        channels: Channel objects; dict form preferred.
        algorithm: desired traversal algorithm

    Return:
        None if there are no shards available, or a mapping of channel URL's to
        ShardBase objects where build_repodata() returns the computed subset..
    """
    channel_data = fetch_channels(channels)
    if channel_data is not None:
        subset = RepodataSubset((*channel_data.values(),))
        subset.reachable(root_packages, strategy=algorithm)
        log.debug("%d (channel, package) nodes discovered", len(subset._nodes))

    return channel_data


# region workers

if TYPE_CHECKING:
    _T = TypeVar("_T")


class QueueCache:
    """
    Implement insert() interface of .cache.ShardCache() as a queue, instead of
    giving network thread direct access to the database.
    """

    def __init__(self, queue):
        self.queue: Queue = queue

    def insert(self, shard: AnnotatedRawShard):
        self.queue.put([shard])

    def copy(self):
        return self  # used for threadsafety in ShardCache; not needed here

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return


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
        for batch in combine_batches_until_none(in_queue):
            node_ids = []
            for item in batch:
                if isinstance(item, AnnotatedRawShard):
                    # opens transaction; could do insertmany here or transaction scoped to loop
                    cache.insert(item)
                else:
                    node_ids.append(item)
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
    cache: ShardCache | QueueCache,
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
        timeout = (
            context.remote_connect_timeout_secs,
            context.remote_read_timeout_secs,
        )
        with s.get(url, timeout=timeout) as response:
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
        # This may be a QueueCache which lets the cache thread serialize access
        # to the database:
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
