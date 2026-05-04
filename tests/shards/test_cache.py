# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Tests for cache functionality with concurrent access and WAL mode."""

from __future__ import annotations

import threading

import zstandard

from _conda.shards.cache import AnnotatedRawShard, ShardCache


class TestCacheWALMode:
    """Tests for Write-Ahead Logging (WAL) mode in cache"""

    def test_shards_cache_uses_wal(self, tmp_path):
        """WAL journal mode is enabled on a fresh cache."""
        with ShardCache(tmp_path) as cache:
            mode = cache.conn.execute("PRAGMA journal_mode").fetchone()[0]
        assert mode == "wal"

    def test_shards_cache_wal_synchronous_pragma(self, tmp_path):
        """Synchronous pragma is set correctly with WAL mode."""
        with ShardCache(tmp_path) as cache:
            # Check that synchronous is set to NORMAL for WAL
            sync = cache.conn.execute("PRAGMA synchronous").fetchone()[0]
            # NORMAL = 1, FULL = 2
            assert sync in (1, 2)  # WAL can use either
            mode = cache.conn.execute("PRAGMA journal_mode").fetchone()[0]
            assert mode == "wal"

    def test_shards_cache_concurrent_read_write(self, tmp_path):
        """Concurrent readers and writers must not raise OperationalError."""
        import msgpack

        compressor = zstandard.ZstdCompressor(level=1)
        errors: list[Exception] = []
        stop = threading.Event()

        def writer(base):
            try:
                with ShardCache(base, create=False) as cache_copy:
                    for i in range(200):
                        if stop.is_set():
                            break
                        shard = AnnotatedRawShard(
                            f"https://shard{i}",
                            f"pkg{i}",
                            compressor.compress(msgpack.dumps({f"pkg{i}": "data"})),
                        )
                        cache_copy.insert(shard)
            except Exception as exc:
                errors.append(exc)

        def reader(base):
            try:
                with ShardCache(base, create=False) as cache_copy:
                    for i in range(200):
                        if stop.is_set():
                            break
                        urls = [f"https://shard{j}" for j in range(i + 1)]
                        cache_copy.retrieve_multiple(urls)
            except Exception as exc:
                errors.append(exc)

        with ShardCache(tmp_path) as cache:
            w = threading.Thread(target=writer, args=(cache.base,))
            r = threading.Thread(target=reader, args=(cache.base,))
            w.start()
            r.start()
            w.join(timeout=10)
            r.join(timeout=10)
            stop.set()

        # No sqlite3.OperationalError from either thread
        assert errors == []

    def test_shards_cache_concurrent_multiple_writers(self, tmp_path):
        """Multiple concurrent writers must not raise OperationalError."""
        import msgpack

        compressor = zstandard.ZstdCompressor(level=1)
        errors: list[Exception] = []
        stop = threading.Event()
        num_writers = 3

        def writer(base, writer_id):
            try:
                with ShardCache(base, create=False) as cache_copy:
                    for i in range(50):
                        if stop.is_set():
                            break
                        shard = AnnotatedRawShard(
                            f"https://writer{writer_id}/shard{i}",
                            f"pkg{writer_id}_{i}",
                            compressor.compress(
                                msgpack.dumps({f"pkg{writer_id}_{i}": "data"})
                            ),
                        )
                        cache_copy.insert(shard)
            except Exception as exc:
                errors.append(exc)

        with ShardCache(tmp_path) as cache:
            threads = []
            for i in range(num_writers):
                t = threading.Thread(target=writer, args=(cache.base, i))
                threads.append(t)
                t.start()

            for t in threads:
                t.join(timeout=10)
            stop.set()

        # No sqlite3.OperationalError from any thread
        assert errors == []
