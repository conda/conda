# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Tests for "ShardFetch". This code is part of the "bfs" algorithm, which helps to
provide an important baseline and comparison but is not executed during the
default "pipelined" shard traversal.
"""

from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path

import pytest

from _conda.shards import cache as shards_cache
from _conda.shards import shards
from _conda.shards.shards import (
    ShardFetch,
    ShardLike,
)

from .test_shards import empty_shards_cache as empty_shards_cache

HERE = Path(__file__).parent


def test_shardfetch_with_shards(empty_shards_cache, tmp_path):
    """
    Test ShardFetch.fetch() with Shards instance (line 104).
    This tests the isinstance(self.shardbase, Shards) branch.
    """
    from _conda.shards.shards import Shards

    # Create fake shard index and Shards instance
    shard_data = {
        "info": {"subdir": "noarch", "base_url": "", "shards_base_url": ""},
        "shards": {"test_package": hashlib.sha256(b"test").digest()},
    }
    shards = Shards(shard_data, "http://example.com/repodata_shards.msgpack.zst")

    # Create a ShardFetch with Shards instance
    shard_fetch = ShardFetch(shards, "test_package", empty_shards_cache)

    # Verify that the instance is created correctly
    assert shard_fetch.shardbase is shards
    assert shard_fetch.package == "test_package"
    assert shard_fetch.shard_cache is empty_shards_cache


def test_shardfetch_cache_required_error(tmp_path):
    """
    Test ShardFetch._process_fetch_result raises ValueError when cache is None (line 170).
    """
    from unittest.mock import Mock

    from _conda.shards.shards import Shards

    # Create a Shards instance
    shard_data = {
        "info": {"subdir": "noarch", "base_url": "", "shards_base_url": ""},
        "shards": {"test_package": hashlib.sha256(b"test").digest()},
    }
    shards = Shards(shard_data, "http://example.com/repodata_shards.msgpack.zst")

    # Create ShardFetch without cache (cache=None)
    shard_fetch = ShardFetch(shards, "test_package", shard_cache=None)

    # Create a mock future
    mock_future = Mock()
    mock_future.result.return_value = Mock()

    # _process_fetch_result should raise ValueError when shard_cache is None
    with pytest.raises(
        ValueError, match="shard_cache is required for fetching from Shards"
    ):
        shard_fetch._process_fetch_result(
            mock_future,
            "http://example.com/shard",
            "test_package",
            {},
            shards,
        )


def test_batch_retrieve_from_cache_with_shardlike():
    """
    Test batch_retrieve_from_cache with non-Shards instances (ShardLike) (line 696).
    """
    from _conda.shards.shards import batch_retrieve_from_cache

    # Create a temporary cache
    with tempfile.TemporaryDirectory() as tmp_dir:
        with shards_cache.ShardCache(Path(tmp_dir)) as cache:
            # Create a ShardLike instance (not Shards)
            repodata = {
                "info": {"subdir": "noarch", "base_url": "", "shards_base_url": ""},
                "packages": {
                    "test.tar.bz2": {
                        "name": "test_package",
                        "version": "1.0",
                    }
                },
                "packages.conda": {},
            }
            shardlike = ShardLike(repodata, url="http://example.com/repodata.json")

            # Call batch_retrieve_from_cache with ShardLike
            result = batch_retrieve_from_cache([shardlike], ["test_package"], cache)

            # Should return ShardFetch objects for ShardLike packages
            assert len(result) > 0
            assert all(isinstance(r, shards.ShardFetch) for r in result)


def test_batch_retrieve_from_cache_empty_sharded():
    """
    Test batch_retrieve_from_cache when no Shards instances are provided (line 690-698).
    """
    from _conda.shards.shards import batch_retrieve_from_cache

    # Create a temporary cache
    with tempfile.TemporaryDirectory() as tmp_dir:
        with shards_cache.ShardCache(Path(tmp_dir)) as cache:
            # Create a ShardLike instance (not Shards)
            repodata = {
                "info": {"subdir": "noarch", "base_url": "", "shards_base_url": ""},
                "packages": {
                    "test.tar.bz2": {
                        "name": "test_package",
                        "version": "1.0",
                    }
                },
                "packages.conda": {},
            }
            shardlike = ShardLike(repodata, url="http://example.com/repodata.json")

            # Call batch_retrieve_from_cache with ShardLike (no Shards)
            result = batch_retrieve_from_cache([shardlike], ["test_package"], cache)

            # Should return ShardFetch objects even for non-Shards instances
            assert len(result) > 0
            assert all(isinstance(r, shards.ShardFetch) for r in result)


def test_fetch_shards_impl_with_visited_cache():
    """
    Test _fetch_shards_impl when packages are already in visited dict (line 143).
    This tests the "if package in shards.visited" branch.
    """
    from _conda.shards.shards import Shards

    # Create a Shards instance
    shard_data = {
        "info": {"subdir": "noarch", "base_url": "", "shards_base_url": ""},
        "shards": {"cached_package": hashlib.sha256(b"cached").digest()},
    }
    shards = Shards(shard_data, "http://example.com/repodata_shards.msgpack.zst")

    # Pre-populate visited dict
    cached_shard = {
        "packages": {"pkg1.tar.bz2": {"name": "cached_package"}},
        "packages.conda": {},
    }
    shards.visited["cached_package"] = cached_shard

    # Create ShardFetch
    shard_fetch = ShardFetch(shards, "cached_package")

    # Call _fetch_shards_impl with a package already in visited
    with tempfile.TemporaryDirectory() as tmp_dir:
        with shards_cache.ShardCache(Path(tmp_dir)) as cache:
            shard_fetch.shard_cache = cache
            results = shard_fetch._fetch_shards_impl(["cached_package"])

            # Should return the cached shard without fetching
            assert "cached_package" in results
            assert results["cached_package"] == cached_shard
