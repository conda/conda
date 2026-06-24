# Sharded repodata

This document provides an overview on how `conda` implements
[CEP-16 Sharded Repodata](https://conda.org/learn/ceps/cep-0016).

Sharded repodata splits `repodata.json` into an index mapping package names to
shard hashes in `repodata_shards.msgpack.zst`. A shard contains repodata for
every package with a given name. Since shards are named after a hash of their
contents, they can be cached without having to check the server for freshness.
Individual shards only need to change when an individual package has changed, so
only the much smaller index has to be re-fetched often.

## Sharded Repodata in conda

Originally developed in `conda-libmamba-solver` and later ported into `conda`,
we wanted a way to implement sharded repodata in Python that was independent of
compiled solver code.

We do this by treating all repodata as if it was sharded repodata. Starting with
a list of installed packages and to-be-installed packages, we gather all
repodata for those packages and look for all package names listed in their
dependencies. We repeat the process for every discovered package name that we
have not already visited, fetching repodata shards or examining all artifacts
with that package name as found in monolithic `repodata.json`. This process
gathers all versions of all packages that we might depend on. We do not consider
package versions at this stage; that's the solver's job.

As of this writing, `conda create -c conda-forge --dry-run python` finds 35
package names; `conda` 137 package names, and `vaex`, a dataframe library with a
complex dependency tree, 678 package names. That's a lot less than the 31k
packages total according to https://conda-forge.org/, and a manageable number to
pre-process in Python before doing a solve with `libmamba`. As long as we can
fetch those packages quickly enough, from cache or from the network, we will
save RAM, disk space, bandwidth and time compared to parsing every package on
the channel every time.

### Threading and concurrency

In order to achieve concurrency, our sharded repodata implementation uses
the Python [threading module](https://docs.python.org/3/library/threading.html).
We have two separate thread workers for fetching cache and network data. These
threads communicate to each other via the following queues:

- **cache_in_queue** every requested shard goes here first where the cache
  worker sees if we have a valid cache record.
- **cache_miss_queue** for every shard not in cache, we send it this queue where
  the network worker thread downloads it.
- **shard_out_queue** once a shard has been fetched from either the cache or
  network worker threads, it is placed here so we can gather all needed
  shards at the end to build our repodata subset.

:::{mermaid}

    sequenceDiagram
        loop
            Main ->> Main: "Fetch" in-memory shard
            Main ->> Cache: Fetch shard
            Cache ->> Network: Cache miss
            Cache ->> Main: Cache hit
            Network ->> Main: Network result
            Main ->> Main: Find new (channel, package) from shard data
        end

:::

## Source code

The shard handling code is split into `conda/_private/shards/shards.py`, `conda/_private/shards/cache.py`,
`conda/_private/shards/subset.py`, `conda/_private/shards/typing.py`, and `conda/_private/shards/misc.py` in `conda/_private/`.
`conda/gateways/shards/` re-exports `build_repodata_subset()`. When
`context.repodata_use_shards` is enabled, `conda/plugins/manager.py` injects it
into solver backends that accept a `build_repodata_subset` constructor parameter.
Solver plugins such as `conda-libmamba-solver` pass the injected callable to
their index helper, which calls it and converts the resulting repodata to solver
objects in memory. If no channel provides sharded repodata,
`build_repodata_subset()` returns `None` and the solver falls back to classic
`repodata.json` loading.

### `conda/_private/shards/shards.py`

`conda/_private/shards/shards.py` provides an interface to treat sharded repodata and monolithic
`repodata.json` in the same way. It checks a channel for sharded repodata,
returning an object that implements the `ShardLike` interface.

### `conda/_private/shards/subset.py`

`conda/_private/shards/subset.py` accepts a list of `ShardLike` instances and a list of initial
packages to compute a repodata subset. The traversal is simplified thanks to the
`ShardLike` interface, so the algorithm doesn't have to worry too much about the
type of each channel.

### `conda/_private/shards/cache.py`

`conda/_private/shards/cache.py` implements a sqlite3 cache used to store individual shards.
When traversing shards, the cache is checked before making a network request.
The shards cache is a single database for all channels in
`$CONDA_PREFIX/pkgs/cache/repodata_shards.db`.

The shards index `repodata_shards.msgpack.zst` is cached in the same way as
`repodata.json`, in individual files in `$CONDA_PREFIX/pkgs/cache/` named after
URL hashes. A `has_<format>` remembers if a channel has shards, or not. If
`has_shards` is `false` then we wait 7 days after `last_checked` to make another
request looking for `repodata_shards.msgpack.zst`. The same system remembers
whether a channel provides `repodata.json.zst`, and stores `ETag` and
`Last-Modified` used to refresh the cache.

```
...
"has_shards": {
    "last_checked": "2025-10-15T17:19:44.408989Z",
    "value": true
},
```

### `conda/_private/shards/typing.py`

`conda/_private/shards/typing.py` provides type hints for data structures used in sharded
repodata, but it is not normative; it only includes fields used by the sharded
repodata system.

### `conda/_private/shards/misc.py`

`conda/_private/shards/misc.py` provides URL helpers, batching utilities, and
connection-pool configuration used by the other shards modules.

### `tests/shards/`

Tests under `tests/shards/` cover the shards-related code in
`conda/_private/shards/*.py`.

## Example dependency graph for Python

This is what Python's dependencies look like on `conda-forge` as of this writing.

If sharded repodata is asked to install Python, we look for `python` in every
active channel. The `python` shard(s) tells us we can fetch `bzip2`, `libffi`,
`...` in parallel, discovering a third layer including `icu`, `ca-certificates`,
and others. `ca-certificates` also depends on some virtual packages, but the
traversal quickly determines that these packages don't appear in any channel by
checking the `repodata_shards.msgpack.zst` index. The solver will let us know if
these missing packages are a problem, virtual or no.

The first draft of sharded repodata in `conda` literally generated classic
`repodata.json` with package subsets to load into the solver, but now the solver
gets a subset that yields individual package records, so that it can convert
each record into solver objects in memory.

The subset gives the solver every possible dependency for a specific request.
The transfer and parsing saved by not processing the full repodata makes up for
the time spent generating a subset.

:::{mermaid} shards_python.mmd
:::
