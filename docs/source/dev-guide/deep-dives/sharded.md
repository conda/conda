# Sharded repodata

This document provides an overview on how `conda` implements
[CEP-16 Sharded Repodata](https://conda.org/learn/ceps/cep-0016).

Sharded repodata is built around two kinds of files:

**Shard index (`repodata_shards.msgpack.zst`)**
: A zstandard-compressed [msgpack](https://msgpack.org/) file stored at
  `<channel>/<subdir>/repodata_shards.msgpack.zst`. It contains a mapping from
  package name to a SHA-256 hash that identifies the corresponding shard. This
  file is small relative to `repodata.json` because it grows only when new
  package *names* are added to the channel, not with every new package build.
  It is served with a short-lived `Cache-Control` `max-age` (typically 60
  seconds to an hour) so that clients pick up new packages promptly.

**Individual shards (`<sha256>.msgpack.zst`)**
: Each shard is a zstandard-compressed msgpack file stored at
  `<shards_base_url><sha256>.msgpack.zst`. It contains the full repodata records
  (equivalent to the relevant slice of `repodata.json`) for every build of a
  single package name. Shards are content-addressable: the filename is the
  lower-case hex SHA-256 hash of the shard's contents. Because the URL changes
  whenever the content changes, shards can be served with
  `Cache-Control: immutable` and cached indefinitely by CDNs and clients alike.

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

## Shard hash validation

CEP-16 specifies that shards are content-addressable: the SHA-256 hash in the
shard's filename is derived from the hash of its contents. This makes it possible
to verify integrity without a round-trip to the server.

**Conda does not validate that a downloaded shard's contents match the SHA-256
hash encoded in its filename.**

This is a deliberate design decision for two reasons:

1. **Performance.** A solve request can involve hundreds of shard fetches.
   Hashing every shard after download would add measurable latency to each
   operation, working against the performance goals that motivated CEP-16 in
   the first place.

2. **Compatibility with certain channel providers.** Some channel providers
   serve sharded repodata in configurations where the content at a given shard
   hash URL cannot be guaranteed to match that hash — for example, when multiple
   upstream sources are aggregated and resolved transparently. Enforcing hash
   validation would break compatibility with these providers.

This behavior is intentional and should not be changed without careful
consideration of both the performance impact and the downstream compatibility
consequences.
