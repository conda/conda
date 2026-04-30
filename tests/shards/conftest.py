# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Sharded repodata test fixtures and utilities.

Adapted from conda-libmamba-solver/tests
"""

from __future__ import annotations

import hashlib
import logging
import tempfile
import time
from contextlib import contextmanager
from typing import TYPE_CHECKING, NamedTuple

import msgpack
import pytest
import zstandard

from _conda.shards import cache as shards_cache
from _conda.shards import core as shards
from _conda.shards import subset as shards_subset
from conda.base.context import context, reset_context
from conda.models.channel import Channel, all_channel_urls

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Iterator
    from pathlib import Path

    from _conda.shards_typing import ShardDict, ShardsIndexDict

# Test channel names
CONDA_FORGE_WITH_SHARDS = "conda-forge"

# Root packages (base environment approximation)
ROOT_PACKAGES = [
    "__archspec",
    "__conda",
    "__osx",
    "__unix",
    "bzip2",
    "ca-certificates",
    "expat",
    "icu",
    "libexpat",
    "libffi",
    "liblzma",
    "libmpdec",
    "libsqlite",
    "libzlib",
    "ncurses",
    "openssl",
    "pip",
    "python",
    "python_abi",
    "readline",
    "tk",
    "twine",
    "tzdata",
    "xz",
    "zlib",
]

# Fake repodata for testing shards
FAKE_REPODATA: ShardDict = {
    "info": {"subdir": "noarch", "base_url": "", "shards_base_url": ""},
    "packages": {
        "foo.tar.bz2": {
            "name": "foo",
            "version": "1",
            "build": "0_a",
            "build_number": 0,
            "depends": ["bar", "baz"],
        },
        "bar.tar.bz2": {
            "name": "bar",
            "version": "1",
            "build": "0_a",
            "build_number": 0,
            "depends": ["foo"],
        },
        "no-matching-conda.tar.bz2": {
            "name": "foo",
            "version": "0.1",
            "build": "0_a",
            "build_number": 0,
        },
    },
    "packages.conda": {
        "foo.conda": {
            "name": "foo",
            "version": "1",
            "build": "0_a",
            "build_number": 0,
            "depends": ["bar", "baz"],
            "constrains": ["splat<3"],
            "sha256": hashlib.sha256().digest(),
        },
        "bar.conda": {
            "name": "bar",
            "version": "1",
            "build": "0_a",
            "build_number": 0,
            "depends": ["foo"],
            "constrains": ["splat<3"],
            "sha256": hashlib.sha256().digest(),
        },
        "no-matching-tar-bz2.conda": {
            "name": "foo",
            "version": "2",
            "build": "0_a",
            "build_number": 0,
            "depends": ["quux", "warble"],
            "constrains": ["splat<3"],
            "sha256": hashlib.sha256().digest(),
        },
    },
    "repodata_version": 2,
}


@contextmanager
def _timer(name: str, callback=None):
    """
    Print measured time with name as part of message. Call
    callback(nanoseconds_elapsed) if given.
    """
    begin = time.monotonic_ns()
    yield
    end = time.monotonic_ns()
    print(f"{name} took {(end - begin) / 1e9:0.6f}s")
    if callback:
        callback(end - begin)


def ensure_hex_hash(repodata: dict):
    """
    Convert every hash in a repodata to hex. Copy repodata.
    """
    new_repodata = {**repodata}
    for group in ("packages", "packages.conda"):
        new_repodata[group] = {}
        for name, record in repodata[group].items():
            record = {**record}
            new_repodata[group][name] = record
            for hash_type in "sha256", "md5":
                if hash_value := record.get(hash_type):
                    if not isinstance(hash_value, str):
                        record[hash_type] = bytes(hash_value).hex()
    return new_repodata


def shard_for_name(repodata: ShardDict, name: str) -> ShardDict:
    """Extract shard containing only packages with given name."""
    return {
        group: {k: v for (k, v) in repodata[group].items() if v["name"] == name}
        for group in ("packages", "packages.conda")
    }


def expand_channels(
    channels: list[Channel], subdirs: Iterable[str] | None = None
) -> dict[str, Channel]:
    """
    Expand channels list into a dict of subdir-aware channels.
    Returns a mapping of channel URL strings to Channel objects.
    """
    # all_channel_urls is from conda.models.channel
    channel_urls = all_channel_urls(
        channels,
        subdirs=subdirs or context.subdirs,
    )
    result = {}
    for url_str in channel_urls:
        result[url_str] = Channel(url_str)
    return result


# Create fake shards for testing
FAKE_SHARD = shard_for_name(FAKE_REPODATA, "foo")
FAKE_SHARD_2 = shard_for_name(FAKE_REPODATA, "bar")


class ShardFactory:
    """
    Create http server shards in a temporary directory. Use this
    class in the context of tests to generate multiple shard servers
    that can be cleaned up after use.
    """

    def __init__(self, root: Path = tempfile.gettempdir()):
        self.root = root
        self._http_servers = []

    def clean_up_http_servers(self):
        """Shutdown all the servers created by this factory."""
        for http in self._http_servers:
            http.shutdown()
        self._http_servers = []

    def http_server_shards(
        self, dir_name: str, finish_request_action: Callable | None = None
    ) -> str:
        """
        Create a new http server serving shards from a temporary directory.

        :param dir_name: The name of the directory to create the shards in.
        :param finish_request_action: Optional callable after each request.
        :return: The URL of the http server serving the shards.
        """
        from . import http_server as http_test_server

        shards_repository = self.root / dir_name / "sharded_repo"
        shards_repository.mkdir(parents=True, exist_ok=True)
        noarch = shards_repository / "noarch"
        noarch.mkdir(exist_ok=True)

        foo_shard = zstandard.compress(msgpack.dumps(FAKE_SHARD))  # type: ignore
        foo_shard_digest = hashlib.sha256(foo_shard).digest()
        (noarch / f"{foo_shard_digest.hex()}.msgpack.zst").write_bytes(foo_shard)

        bar_shard = zstandard.compress(msgpack.dumps(FAKE_SHARD_2))  # type: ignore
        bar_shard_digest = hashlib.sha256(bar_shard).digest()
        (noarch / f"{bar_shard_digest.hex()}.msgpack.zst").write_bytes(bar_shard)

        # Create fake repodata_shards.msgpack.zst index
        index: ShardsIndexDict = {
            "info": {"subdir": "noarch", "base_url": "", "shards_base_url": ""},
            "version": 1,
            "shards": {
                "foo": bytes.fromhex(foo_shard_digest.hex()),
                "bar": bytes.fromhex(bar_shard_digest.hex()),
            },
        }
        index_data = zstandard.compress(msgpack.dumps(index))  # type: ignore
        (noarch / "repodata_shards.msgpack.zst").write_bytes(index_data)

        def handler(request, base_path):
            try:
                http_test_server.request_handler(request, base_path)
                if finish_request_action:
                    finish_request_action(request)
            except Exception:
                if finish_request_action:
                    finish_request_action(request)
                raise

        server = http_test_server.run_server(
            handler, "127.0.0.1", base_path=str(shards_repository)
        )
        self._http_servers.append(server)

        return f"http://{server.server_name}:{server.server_port}"


class MockCache(NamedTuple):
    """Contain all the elements needed by mock_cache fixture."""

    num_shards: int
    shards: list[shards_cache.AnnotatedRawShard]
    cache: shards_cache.ShardCache


@pytest.fixture
def prepare_shards_test(monkeypatch: pytest.MonkeyPatch):
    """
    Reset token to avoid being logged in. Enable shards.
    """
    logging.basicConfig(level=logging.INFO)
    for module in (shards, shards_cache, shards_subset):
        module.log.setLevel(logging.DEBUG)

    monkeypatch.setenv("CONDA_TOKEN", "")
    monkeypatch.setenv("CONDA_PLUGINS_USE_SHARDED_REPODATA", "1")
    reset_context()
    # Note: _is_sharded_repodata_enabled() is from conda-libmamba-solver
    # For now we just ensure the env var is set


@pytest.fixture()
def mock_cache(tmp_path: Path) -> Iterator[MockCache]:
    """
    Set up a mock shard cache that will be used by multiple benchmark tests.
    """
    num_fake_shards = 64
    with shards_cache.ShardCache(tmp_path) as cache:
        fake_shards = []

        compressor = zstandard.ZstdCompressor(level=1)
        for i in range(num_fake_shards):
            fake_shard = {f"foo{i}": "bar"}
            annotated_shard = shards_cache.AnnotatedRawShard(
                f"https://foo{i}",
                f"foo{i}",
                compressor.compress(msgpack.dumps(fake_shard)),  # type: ignore
            )
            cache.insert(annotated_shard)
            fake_shards.append(annotated_shard)

        yield MockCache(num_shards=num_fake_shards, shards=fake_shards, cache=cache)


@pytest.fixture
def shard_cache_with_data(
    mock_cache: MockCache,
) -> tuple[shards_cache.ShardCache, list[shards_cache.AnnotatedRawShard]]:
    """
    ShardCache with some data already inserted.
    """
    return mock_cache.cache, mock_cache.shards


@pytest.fixture(scope="session")
def http_server_shards(tmp_path_factory) -> Iterable[str]:
    """
    A shard repository with sharded repodata.
    """
    shard_factory = ShardFactory(tmp_path_factory.mktemp("sharded_repo"))
    url = shard_factory.http_server_shards("http_server_shards")
    yield url
    shard_factory.clean_up_http_servers()


@pytest.fixture
def shard_factory(tmp_path_factory, request: pytest.FixtureRequest) -> ShardFactory:
    """
    Use ShardFactory to manage creating and cleaning up shards for testing.

    Example:

    ```
    def test_something(shard_factory: ShardFactory):
        server_one = shard_factory.http_server_shards("one")
        server_two = shard_factory.http_server_shards("two")
        ...
    ```
    """
    shards_repository = tmp_path_factory.mktemp("sharded_repo")
    factory = ShardFactory(shards_repository)

    def close_servers():
        factory.clean_up_http_servers()

    request.addfinalizer(close_servers)
    return factory
