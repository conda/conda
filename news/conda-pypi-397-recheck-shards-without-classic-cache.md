### Bug fixes

* If shards were not found on a channel, conda would cache the not-found response, which can break shards-only channels. Instead, always check for sharded repodata if classic repodata has not been cached. (#16183)
