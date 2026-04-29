# Copyright (C) 2022 Anaconda, Inc
# Copyright (C) 2023 conda
# SPDX-License-Identifier: BSD-3-Clause
"""
Cache suitable for shards, not allowed to change because they are named
after their own sha256 hash.
"""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass
from typing import TYPE_CHECKING

import msgpack
import zstandard

if TYPE_CHECKING:
    from pathlib import Path

    from .shards_typing import ShardDict

log = logging.getLogger(__name__)

SHARD_CACHE_NAME = "repodata_shards.db"
ZSTD_MAX_SHARD_SIZE = 2**20 * 16  # maximum size necessary when compresed data has no size header


@dataclass
class AnnotatedRawShard:
    def __init__(self, url: str, package: str, compressed_shard: bytes):
        # prevent easy mistake of swapping url, package
        assert "://" in url
        assert "://" not in package

        self.url = url
        self.package = package  # remove this field to avoid confusion?
        self.compressed_shard = compressed_shard

    url: str
    package: str
    compressed_shard: bytes


def connect(dburi="cache.db"):
    """
    Get database connection.

    dburi: uri-style sqlite database filename; accepts certain ?= parameters.
    """
    conn = sqlite3.connect(dburi, uri=True)
    conn.row_factory = sqlite3.Row
    with conn as c:
        c.execute("PRAGMA foreign_keys = ON")
    return conn


class ShardCache:
    """
    Handle caching for individual shards (not the index of shards).
    """

    def __init__(self, base: Path, create=True):
        """
        base: directory and filename prefix for cache.
        """
        self.base = base
        self.connect(create=create)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exec_tb):
        self.close()

    def close(self):
        """
        Clean up connection. ShardCache can no longer be used after close().
        """
        if self.conn:
            self.conn.close()
            self.conn = None

    def copy(self):
        """
        Copy cache with new connection. Useful for threads.
        """
        return ShardCache(self.base, create=False)

    def connect(self, create=True, retry=True):
        """
        Args:
            create: if True, create table if not exists.
            retry: remove cache, log warning, and retry on error.
        """
        global SHARD_CACHE_NAME

        dburi = (self.base / SHARD_CACHE_NAME).as_uri()
        self.conn = connect(dburi)
        if not create:
            return
        try:
            # this schema will also get confused if we merge packages into a single
            # shard, but the package name should be advisory.
            with self.conn as c:
                c.execute(
                    "CREATE TABLE IF NOT EXISTS shards ("
                    "url TEXT PRIMARY KEY, package TEXT, shard BLOB, "
                    "timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
                )
        except sqlite3.DatabaseError as e:
            # Python 3.11 adds sqlite_errorcode. This is meant to delete and
            # retry on all DatabaseError for Python 3.10, but on Python 3.11+
            # only retry on SQLITE_NOTADB. Other errors e.g. busy, locked, would
            # propagate.
            has_errorcode = hasattr(e, "sqlite_errorcode")
            if retry and ((not has_errorcode) or (e.sqlite_errorcode == sqlite3.SQLITE_NOTADB)):
                log.warning("%s '%s'; remove and retry.", dburi, e)
                try:
                    self.remove_cache()
                except OSError as e:
                    # alternate filename if primary cannot be removed.
                    log.warning("%s '%s'; use alternate filename.", dburi, e)
                    SHARD_CACHE_NAME = "repodata_shards_1.db"
                # pass False so that we only retry once:
                return self.connect(create=create, retry=False)
            raise

    def insert(self, raw_shard: AnnotatedRawShard):
        """
        Args:
            url: of shard
            package: package name
            raw_shard: msgpack.zst compressed shard data
        """
        # decompress and return shard for convenience, also to validate? unless
        # caller would rather retrieve the shard from another thread.
        with self.conn as c:
            c.execute(
                "INSERT OR IGNORE INTO SHARDS (url, package, shard) VALUES (?, ?, ?)",
                (raw_shard.url, raw_shard.package, raw_shard.compressed_shard),
            )

    def retrieve(self, url) -> ShardDict | None:
        with self.conn as c:
            row = c.execute("SELECT shard FROM shards WHERE url = ?", (url,)).fetchone()
            return (
                msgpack.loads(
                    zstandard.decompress(row["shard"], max_output_size=ZSTD_MAX_SHARD_SIZE)
                )
                if row
                else None
            )  # type: ignore

    def retrieve_multiple(self, urls: list[str]) -> dict[str, ShardDict | None]:
        """
        Query database for cached shard urls.

        Return a dict of urls in cache mapping to the Shard or None if not present.
        """
        if not urls:
            return {}  # this optimization does not save a noticeable amount of time.

        # In one test reusing the context saves difference between .006s and .01s
        # We could make this a threadlocal.
        dctx = zstandard.ZstdDecompressor()

        query = f"SELECT url, shard FROM shards WHERE url IN ({','.join(('?',) * len(urls))}) ORDER BY url"
        with self.conn as c:
            result: dict[str, ShardDict | None] = {
                row["url"]: msgpack.loads(
                    dctx.decompress(row["shard"], max_output_size=ZSTD_MAX_SHARD_SIZE)
                )
                if row
                else None
                for row in c.execute(query, urls)  # type: ignore
            }
            return result

    def clear_cache(self):
        """
        Truncate the database by removing all rows from tables
        """
        with self.conn as c:
            c.execute("DELETE FROM shards")

    def remove_cache(self):
        """
        Remove the sharded cache database.
        """
        self.close()
        try:
            (self.base / SHARD_CACHE_NAME).unlink()
        except OSError:
            # possibly workable on Windows
            (self.base / SHARD_CACHE_NAME).rename(self.base / f"{SHARD_CACHE_NAME}.conda_trash")
