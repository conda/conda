# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Sharded repodata test fixtures and utilities.

Adapted from conda-libmamba-solver/tests
"""

from __future__ import annotations

import contextlib
import hashlib
import http.server
import logging
import queue
import socket
import tempfile
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple

import msgpack
import pytest

from conda._private.shards import cache, shards, subset
from conda._private.zstd import zstd
from conda.base.context import context, reset_context
from conda.models.channel import Channel, all_channel_urls

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Iterator

    from conda._private.shards.typing import RepodataDict, ShardDict, ShardsIndexDict

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
FAKE_REPODATA: RepodataDict = {
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


def _run_test_server(
    directory: str, finish_request_action: Callable | None = None
) -> http.server.ThreadingHTTPServer:
    """
    Run a test server on a random port serving files from a directory.

    Adapted from conda-libmamba-solver/tests/http_test_server.py

    :param directory: The directory to serve files from
    :param finish_request_action: Optional callable after each request
    :return: The running ThreadingHTTPServer instance
    """

    class DualStackServer(http.server.ThreadingHTTPServer):
        daemon_threads = False  # Per-request threads
        allow_reuse_address = True  # Good for tests
        request_queue_size = 64  # Should be more than test packages

        def server_bind(self):
            # Suppress exception when protocol is IPv4
            with contextlib.suppress(Exception):
                self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
            return super().server_bind()

        def finish_request(self, request, client_address):
            if finish_request_action:
                finish_request_action()
            self.RequestHandlerClass(request, client_address, self, directory=directory)

    def start_server(q: queue.Queue):
        try:
            with DualStackServer(
                ("127.0.0.1", 0), http.server.SimpleHTTPRequestHandler
            ) as httpd:
                q.put(httpd)
                try:
                    httpd.serve_forever()
                except KeyboardInterrupt:
                    pass
        except Exception as exc:
            q.put(exc)

    started: queue.Queue = queue.Queue()
    threading.Thread(target=start_server, args=(started,), daemon=True).start()

    result = started.get(timeout=1)
    if isinstance(result, Exception):
        raise result
    return result


class ShardFactory:
    """
    Create http server shards in a temporary directory. Use this
    class in the context of tests to generate multiple shard servers
    that can be cleaned up after use.

    Adapted from conda-libmamba-solver/tests/test_shards.py

    Example:

    ```
    # create shard factory with its root in a temporary directory
    shard_factory = ShardFactory(tmp_path_factory.mktemp("sharded_repo"))

    # create an http server serving the testing data
    url = shard_factory.http_server_shards("http_server_shards")

    # make a request to the server
    # ... use the url ...

    # shutdown all servers created by this factory
    shard_factory.clean_up_http_servers()
    ```
    """

    def __init__(self, root: Path | str = tempfile.gettempdir()):
        self.root = Path(root)
        self._http_servers = []

    def clean_up_http_servers(self):
        """Shutdown all the servers created by this factory."""
        for httpd in self._http_servers:
            httpd.shutdown()
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
        shards_repository = self.root / dir_name / "sharded_repo"
        shards_repository.mkdir(parents=True, exist_ok=True)
        noarch = shards_repository / "noarch"
        noarch.mkdir(exist_ok=True)

        foo_shard = zstd.compress(msgpack.dumps(FAKE_SHARD))  # type: ignore
        foo_shard_digest = hashlib.sha256(foo_shard).digest()
        (noarch / f"{foo_shard_digest.hex()}.msgpack.zst").write_bytes(foo_shard)

        bar_shard = zstd.compress(msgpack.dumps(FAKE_SHARD_2))  # type: ignore
        bar_shard_digest = hashlib.sha256(bar_shard).digest()
        (noarch / f"{bar_shard_digest.hex()}.msgpack.zst").write_bytes(bar_shard)

        # Create fake malformed shards to test error handling
        malformed = {"follows_schema": False}
        bad_schema = zstd.compress(msgpack.dumps(malformed))  # type: ignore
        malformed_digest = hashlib.sha256(bad_schema).digest()
        (noarch / f"{malformed_digest.hex()}.msgpack.zst").write_bytes(bad_schema)

        not_zstd = b"not zstd"
        (noarch / f"{hashlib.sha256(not_zstd).digest().hex()}.msgpack.zst").write_bytes(
            not_zstd
        )

        not_msgpack = zstd.compress(b"not msgpack")
        (
            noarch / f"{hashlib.sha256(not_msgpack).digest().hex()}.msgpack.zst"
        ).write_bytes(not_msgpack)

        # Create fake repodata_shards.msgpack.zst index
        fake_shards: ShardsIndexDict = {
            "info": {"subdir": "noarch", "base_url": "", "shards_base_url": ""},
            "version": 1,
            "shards": {
                "foo": foo_shard_digest,
                "bar": bar_shard_digest,
                "wrong_package_name": foo_shard_digest,
                "fake_package": b"",
                "malformed": malformed_digest,
                "not_zstd": hashlib.sha256(not_zstd).digest(),
                "not_msgpack": hashlib.sha256(not_msgpack).digest(),
            },
        }
        index_data = zstd.compress(msgpack.dumps(fake_shards))  # type: ignore
        (noarch / "repodata_shards.msgpack.zst").write_bytes(index_data)

        httpd = _run_test_server(
            str(shards_repository), finish_request_action=finish_request_action
        )
        self._http_servers.append(httpd)

        host, port = httpd.socket.getsockname()[:2]
        url_host = f"[{host}]" if ":" in host else host
        return f"http://{url_host}:{port}/"


class MockCache(NamedTuple):
    """Contain all the elements needed by mock_cache fixture."""

    num_shards: int
    shards: list[cache.AnnotatedRawShard]
    cache_obj: cache.ShardCache


@pytest.fixture
def prepare_shards_test(monkeypatch: pytest.MonkeyPatch):
    """
    Reset token to avoid being logged in. Enable shards.
    """
    logging.basicConfig(level=logging.INFO)
    for module in (shards, cache, subset):
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
    with cache.ShardCache(tmp_path) as cache_instance:
        fake_shards = []

        for i in range(num_fake_shards):
            fake_shard = {f"foo{i}": "bar"}
            annotated_shard = cache.AnnotatedRawShard(
                f"https://foo{i}",
                f"foo{i}",
                zstd.compress(msgpack.dumps(fake_shard), level=1),  # type: ignore
            )
            cache_instance.insert(annotated_shard)
            fake_shards.append(annotated_shard)

        yield MockCache(
            num_shards=num_fake_shards, shards=fake_shards, cache_obj=cache_instance
        )


@pytest.fixture
def shard_cache_with_data(
    mock_cache: MockCache,
) -> tuple[cache.ShardCache, list[cache.AnnotatedRawShard]]:
    """
    ShardCache with some data already inserted.
    """
    return mock_cache.cache_obj, mock_cache.shards


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
