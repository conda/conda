# Sharded repodata implementation

This document provides an overview on how `conda` implements
[CEP-16 Sharded Repodata](https://conda.org/learn/ceps/cep-0016).

Sharded repodata splits `repodata.json` into an index mapping package names to
shard hashes in `repodata_shards.msgpack.zst`. A shard contains repodata for
every package with a given name. Since shards are named after a hash of their
contents, they can be cached without having to check the server for freshness.
Individual shards only need to change when an individual package has changed, so
only the much smaller index has to be re-fetched often.

## Sharded Repodata in conda-libmamba-solver

For `conda-libmamba-solver`, we wanted a way to implement sharded repodata in
Python without having to touch the C++ `libmamba`.

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

The shard handling code is split into `shards.py`, `shards_cache.py`,
`shards_subset.py` and `shards_typing.py` in `conda_libmamba_solver/`.
Additional code in `conda_libmamba_solver/index.py` calls
`build_repodata_subset()` and converts the resulting repodata to `libmamba`
objects.

### `shards.py`

`shards.py` provides an interface to treat sharded repodata and monolithic
`repodata.json` in the same way. It checks a channel for sharded repodata,
returning an object that implements the `ShardLike` interface.

### `shards_subset.py`

`shards_subset.py` accepts a list of `ShardLike` instances and a list of initial
packages to compute a repodata subset. The traversal is simplified thanks to the
`ShardLike` interface, so the algorithm doesn't have to worry too much about the
type of each channel.

### `shards_cache.py`

`shards_cache.py` implements a sqlite3 cache used to store individual shards.
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

### `shards_typing.py`

`shards_typing.py` provides type hints for data structures used in sharded
repodata, but it is not normative; it only includes fields used by the sharded
repodata system.

### `tests/test_shards.py`

The sharded repodata tests maintain 100% code coverage of the shards-related code
`shards*.py`.

## Example dependency graph for Python

This is what Python's dependencies look like on `conda-forge` as of this writing.

If sharded repodata is asked to install Python, we look for `python` in every
active channel. The `python` shard(s) tells us we can fetch `bzip2`, `libffi`,
`...` in parallel, discovering a third layer including `icu`, `ca-certificates`,
and others. `ca-certificates` also depends on some virtual packages, but the
traversal quickly determine that these packages don't appear in any channel by
checking the `repodata_shards.msgpack.zst` index. The solver will let us know if
these missing packages are a problem, virtual or no.

The first draft of sharded repodata in `conda-libmamba-solver` literally
generated classic `repodata.json` with package subsets to load into the solver,
but now we convert each record into `libmamba` `PackageInfo` objects in memory.

By giving `libmamba` every possible dependency for a specific request, it has
enough information to produce a solution.

:::{mermaid} shards_python.mmd
