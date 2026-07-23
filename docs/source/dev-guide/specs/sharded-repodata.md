# Sharded repodata

Conda implements [CEP-16 Sharded Repodata](https://conda.org/learn/ceps/cep-0016), a
repodata format designed for sparse, incremental fetching. Rather than downloading a
single monolithic `repodata.json` for an entire channel, conda can fetch only the
repodata it needs by following a content-addressable shard index.

:::{seealso}
{doc}`../deep-dives/sharded` covers the full implementation in detail: the threading
model, source layout, SQLite shard cache, and an example dependency graph for Python.
:::

## Overview

Sharded repodata is built around two kinds of files:

**Shard index (`repodata_shards.msgpack.zst`)**
: A zstandard-compressed [msgpack](https://msgpack.org/) file stored at
  `<channel>/<subdir>/repodata_shards.msgpack.zst`. It contains a mapping from package
  name to a SHA-256 hash that identifies the corresponding shard. This file is small
  relative to `repodata.json` because it grows only when new package *names* are added
  to the channel, not with every new package build. It is served with a short-lived
  `Cache-Control` `max-age` (typically 60 seconds to an hour) so that clients pick up
  new packages promptly.

**Individual shards (`<sha256>.msgpack.zst`)**
: Each shard is a zstandard-compressed msgpack file stored at
  `<shards_base_url><sha256>.msgpack.zst`. It contains the full repodata records
  (equivalent to the relevant slice of `repodata.json`) for every build of a single
  package name. Shards are content-addressable: the filename is the lower-case hex
  SHA-256 hash of the shard's contents. Because the URL changes whenever the content
  changes, shards can be served with `Cache-Control: immutable` and cached
  indefinitely by CDNs and clients alike.

### Fetch algorithm

To build a repodata subset for a given solve request, conda follows this iterative
process:

1. Fetch the shard index `repodata_shards.msgpack.zst`. Standard HTTP caching applies.
2. Collect the initial set of package names from the packages being installed and
   already installed in the target environment.
3. For each package name in the set, look up its shard hash in the index and fetch the
   shard (from the local SQLite cache if available, otherwise from the network).
4. Parse the shard records and collect all package names referenced in the dependency
   fields.
5. Add any newly discovered package names to the set and repeat from step 3 until no
   new names are found.
6. Pass the accumulated repodata subset to the solver.

This traversal means that for most requests conda fetches a small fraction of the
total channel repodata. For example, installing Python from conda-forge requires
repodata for roughly 35 package names rather than the channel's full 31,000+.

## Conda's implementation

Conda treats sharded and monolithic `repodata.json` channels uniformly through a
`ShardLike` interface. The fetch loop described above is implemented in
`conda/_private/shards/subset.py` and uses two background threads — one for cache
lookups and one for network downloads — that communicate via queues to maximise
concurrency.

When `context.repodata_use_shards` is enabled, `conda/plugins/manager.py` injects the
`build_repodata_subset()` callable (re-exported from `conda/gateways/shards/`) into
solver backends that accept it. If a channel does not provide sharded repodata,
`build_repodata_subset()` returns `None` and conda falls back to loading the full
`repodata.json`.

See {doc}`../deep-dives/sharded` for the complete source layout, caching details,
and an annotated dependency-graph example.

## Shard hash validation

CEP-16 specifies that shards are content-addressable: the SHA-256 hash in the shard's
filename is derived from the hash of its contents. This makes it possible to verify
integrity without a round-trip to the server.

**Conda does not validate that a downloaded shard's contents match the SHA-256 hash
encoded in its filename.**

This is a deliberate design decision for two reasons:

1. **Performance.** A solve request can involve hundreds of shard fetches. Hashing
   every shard after download would add measurable latency to each operation, working
   against the performance goals that motivated CEP-16 in the first place.

2. **Compatibility with certain channel providers.** Some channel providers serve
   sharded repodata in configurations where the content at a given shard hash URL
   cannot be guaranteed to match that hash — for example, when multiple upstream
   sources are aggregated and resolved transparently. Enforcing hash validation would
   break compatibility with these providers.

This behavior is intentional and should not be changed without careful consideration
of both the performance impact and the downstream compatibility consequences.
