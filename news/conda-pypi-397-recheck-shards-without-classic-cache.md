### Bug fixes

* Fix sharded repodata fetching to recheck shards when a cached negative shard-format result has no classic repodata cache to fall back to, avoiding stale-cache failures for shards-only channels. (#16183)
