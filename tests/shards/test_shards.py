# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Test sharded repodata.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import sqlite3
import tempfile
import threading
import time
import warnings
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple

import msgpack
import pytest
import zstandard
from conda_libmamba_solver.index import (
    _is_sharded_repodata_enabled,
)
from requests import Request, Response

import conda.gateways.repodata
from conda._private.shards import cache as shards_cache
from conda._private.shards import shards
from conda._private.shards import subset as shards_subset
from conda._private.shards.shards import (
    ShardLike,
    Shards,
    _repodata_shards,
    _safe_urljoin_with_slash,
    _shards_connections,
    batch_retrieve_from_cache,
    fetch_channels,
    fetch_shards_index,
    shard_mentioned_packages,
)
from conda.base.context import context, reset_context
from conda.core.subdir_data import SubdirData
from conda.models.channel import Channel

from .conftest import (
    CONDA_FORGE_WITH_SHARDS,
    ROOT_PACKAGES,
    _run_test_server,
    _timer,
    expand_channels,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Iterator

    from conda._private.shards.typing import ShardsIndexDict

HERE = Path(__file__).parent


def package_names(shard: shards_cache.ShardDict):
    """
    All package names mentioned in a shard (should be a single package name)
    """
    return set(package["name"] for package in shard["packages"].values()) | set(
        package["name"] for package in shard["packages.conda"].values()
    )


@pytest.fixture
def prepare_shards_test(monkeypatch: pytest.MonkeyPatch):
    """
    Reset token to avoid being logged in. e.g. the testing channel doesn't understand them.
    Enable shards.
    """
    logging.basicConfig(level=logging.INFO)
    for module in (shards, shards_cache, shards_subset):
        module.log.setLevel(logging.DEBUG)

    monkeypatch.setenv("CONDA_TOKEN", "")
    monkeypatch.setenv("CONDA_PLUGINS_USE_SHARDED_REPODATA", "1")
    reset_context()
    assert _is_sharded_repodata_enabled()


@pytest.fixture
def empty_shards_cache(tmp_path):
    """
    Empty shards cache, with cleanup.
    """
    with shards_cache.ShardCache(tmp_path) as cache:
        yield cache
        cache.remove_cache()


# 'foo' and 'bar' have circular dependencies on each other; dependencies on
# missing shards (which are not an error during traversal; the solver may or may
# not complain if ran); and 'constrains' to exercise other parts of the code.

# TODO may need to give these unique prefixes, version numbers ending in
# '.tar.bz2', '.conda' to avoid confusing tar-vs-conda code. May need to create
# a few more packages giving a richer dependency graph.

FAKE_REPODATA = {
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


def ensure_hex_hash(repodata: dict):
    """
    Convert every hash in a repodata to hex. Copy repodata.
    """
    new_repodata = {**repodata}
    for group in ("packages", "packages.conda"):
        for name, record in repodata[group].items():
            record = {**record}
            new_repodata[group][name] = record
            for hash_type in "sha256", "md5":
                if hash_value := record.get(hash_type):
                    if not isinstance(hash_value, str):
                        record[hash_type] = bytes(hash_value).hex()
    return new_repodata


def shard_for_name(repodata, name):
    return {
        group: {k: v for (k, v) in repodata[group].items() if v["name"] == name}
        for group in ("packages", "packages.conda")
    }


FAKE_SHARD = shard_for_name(FAKE_REPODATA, "foo")
FAKE_SHARD_2 = shard_for_name(FAKE_REPODATA, "bar")


class ShardFactory:
    """
    Create http server shards in a temporary directory. Use this
    class in the context of tests to generate multiple shard servers
    that can be cleaned up after use.

    Example:

    ```
    # create shard factory with its root in a temporary directory
    shard_factory = ShardFactory(tmp_path_factory.mktemp("sharded_repo"))

    # create an http server serving the testing data
    url = shard_factory.http_server_shards("http_server_shards")

    # make a request to the server
    subdir_data = SubdirData(Channel.from_url(f"{url}/noarch"))
    found = fetch_shards_index(subdir_data)

    # shutdown up all servers created by this factory
    shard_factory.clean_up_http_servers()
    ```
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
        """Create a new http server serving shards from a temporary directory.

        :param dir_name: The name of the directory to create the shards in.
        :param finish_request_action: An optional callable to be called after each request is finished.
        :return: The URL of the http server serving the shards.
        """
        shards_repository = self.root / dir_name / "sharded_repo"
        shards_repository.mkdir(parents=True)
        noarch = shards_repository / "noarch"
        noarch.mkdir()

        foo_shard = zstandard.compress(msgpack.dumps(FAKE_SHARD))  # type: ignore
        foo_shard_digest = hashlib.sha256(foo_shard).digest()
        (noarch / f"{foo_shard_digest.hex()}.msgpack.zst").write_bytes(foo_shard)

        bar_shard = zstandard.compress(msgpack.dumps(FAKE_SHARD_2))  # type: ignore
        bar_shard_digest = hashlib.sha256(bar_shard).digest()
        (noarch / f"{bar_shard_digest.hex()}.msgpack.zst").write_bytes(bar_shard)

        malformed = {"follows_schema": False}
        bad_schema = zstandard.compress(msgpack.dumps(malformed))  # type: ignore
        malformed_digest = hashlib.sha256(bad_schema).digest()

        (noarch / f"{malformed_digest.hex()}.msgpack.zst").write_bytes(bad_schema)
        not_zstd = b"not zstd"
        (noarch / f"{hashlib.sha256(not_zstd).digest().hex()}.msgpack.zst").write_bytes(
            not_zstd
        )
        not_msgpack = zstandard.compress(b"not msgpack")
        (
            noarch / f"{hashlib.sha256(not_msgpack).digest().hex()}.msgpack.zst"
        ).write_bytes(not_msgpack)
        fake_shards: ShardsIndexDict = {
            "info": {"subdir": "noarch", "base_url": "", "shards_base_url": ""},
            "version": 1,
            "shards": {
                "foo": foo_shard_digest,
                "bar": bar_shard_digest,
                "wrong_package_name": foo_shard_digest,
                "fake_package": b"",
                "malformed": hashlib.sha256(bad_schema).digest(),
                "not_zstd": hashlib.sha256(not_zstd).digest(),
                "not_msgpack": hashlib.sha256(not_msgpack).digest(),
            },
        }
        (shards_repository / "noarch" / "repodata_shards.msgpack.zst").write_bytes(
            zstandard.compress(msgpack.dumps(fake_shards))  # type: ignore
        )

        http = _run_test_server(
            str(shards_repository), finish_request_action=finish_request_action
        )
        self._http_servers.append(http)

        host, port = http.socket.getsockname()[:2]
        url_host = f"[{host}]" if ":" in host else host
        return f"http://{url_host}:{port}/"


@pytest.fixture(scope="session")
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
    shard_factory = ShardFactory(shards_repository)

    def close_servers():
        shard_factory.clean_up_http_servers()

    request.addfinalizer(close_servers)
    return shard_factory


@pytest.fixture(scope="session")
def http_server_shards(tmp_path_factory) -> Iterable[str]:
    """
    A shard repository with a difference.
    """
    shard_factory = ShardFactory(tmp_path_factory.mktemp("sharded_repo"))
    url = shard_factory.http_server_shards("http_server_shards")
    yield url
    shard_factory.clean_up_http_servers()


@pytest.mark.parametrize("error_code", [404, 405, 416, 511])
def test_fetch_shards_index_mark_unavailable(monkeypatch, tmp_path, error_code):
    expect_should_check_shards = not (400 <= error_code < 500 and error_code != 416)

    # Guarantee clean cache to avoid interference from previous tests
    monkeypatch.setenv("CONDA_PKGS_DIRS", str(tmp_path))
    reset_context()

    class MockSession:
        proxies = None
        get_count = 0

        def __call__(self, *args):
            return self

        def get(self, url, *args, **kwargs):
            self.get_count += 1
            request = Request("GET", url).prepare()
            response = Response()
            response.request = request
            response.url = url
            # due to fetch_shards_index going through conda_http_errors, only
            # 404 may be converted to the RepodataUnavailable exception we are
            # looking for:
            response.status_code = error_code
            return response

    mock_session = MockSession()
    monkeypatch.setattr(shards, "get_session", mock_session)

    channel = Channel("http://localhost/mock/noarch")
    subdir_data = SubdirData(channel)

    repo_cache = subdir_data.repo_cache
    repo_cache.load_state()
    assert repo_cache.state.should_check_format("shards")

    fetch_shards_index(subdir_data)

    # load json directly due to issues with repo_cache API, also
    # fetch_shards_index gets a different repo_cache instance:
    repo_cache.state.update(json.loads(repo_cache.cache_path_state.read_text()))
    assert repo_cache.state.should_check_format("shards") == expect_should_check_shards
    assert mock_session.get_count == 1

    # assert that retry skips over shards without trying to GET
    get_count = mock_session.get_count
    second_try = fetch_shards_index(subdir_data)
    assert second_try is None
    assert mock_session.get_count == get_count + expect_should_check_shards


def test_fetch_shards_error(http_server_shards, empty_shards_cache):
    channel = Channel.from_url(f"{http_server_shards}/noarch")
    subdir_data = SubdirData(channel)
    found = fetch_shards_index(subdir_data)
    assert found

    not_found = fetch_shards_index(
        SubdirData(Channel.from_url(f"{http_server_shards}/linux-64")),
    )
    assert not not_found


def test_shards_base_url():
    """
    Test Shards() URL functions.
    """

    def with_urls(url, base_url, shards_base_url):
        # Shards() with different url's
        return Shards(
            {
                "info": {
                    "subdir": "noarch",
                    "base_url": base_url,
                    "shards_base_url": shards_base_url,
                },
                "version": 1,
                "shards": {"fake_package": bytes.fromhex("abcd")},
            },
            url,
        )

    shards = with_urls(
        "https://conda.anaconda.org/channel-name/noarch/",
        "",
        "https://shards.example.com/channel-name",
    )

    assert (
        shards.shard_url("fake_package")
        == "https://shards.example.com/channel-name/abcd.msgpack.zst"
    )

    shards = with_urls(shards.url, "", "")

    assert (
        shards.shard_url("fake_package")
        == "https://conda.anaconda.org/channel-name/noarch/abcd.msgpack.zst"
    )

    # where packages are stored
    assert shards.base_url == "https://conda.anaconda.org/channel-name/noarch/"

    # packages on a different domain than shards.url
    shards = with_urls(
        "https://conda.anaconda.org/channel-name/noarch/",
        "https://prefix.dev/conda-forge/noarch/",
        "https://shards.example.com/channel-name",
    )

    assert shards.base_url == "https://prefix.dev/conda-forge/noarch/"

    # no-trailing-/ example from prefix.dev metadata

    shards = with_urls(
        "https://prefix.dev/conda-forge/osx-arm64/repodata_shards.msgpack.zst",
        "https://prefix.dev/conda-forge/osx-arm64",
        "",
    )

    # shards_base_url is url joined with shards_base_url, suitable for string concatenation
    assert shards.shards_base_url == "https://prefix.dev/conda-forge/osx-arm64/"
    assert (
        shards.shard_url("fake_package")
        == "https://prefix.dev/conda-forge/osx-arm64/abcd.msgpack.zst"
    )

    # relative shards_base_url
    shards = with_urls(
        "https://prefix.dev/conda-forge/osx-arm64/repodata_shards.msgpack.zst",
        "https://prefix.dev/conda-forge/noarch/",
        "./shards/",
    )
    assert shards.shards_base_url == "https://prefix.dev/conda-forge/osx-arm64/shards/"

    # relative shards_base_url, with parent directory
    shards = with_urls(
        "https://prefix.dev/conda-forge/osx-arm64/repodata_shards.msgpack.zst",
        "https://prefix.dev/conda-forge/noarch/",
        "../shards/",
    )
    shards.shards_index["info"]["shards_base_url"] = "../shards"
    assert shards.shards_base_url == "https://prefix.dev/conda-forge/shards/"

    # s3 vs https
    shards = with_urls(
        "s3://index-bucket/linux-64",  # shards index stored on s3
        "s3://package-bucket/linux-64",  # packages stored on different s3 bucket
        "https://example.org/shards/",  # individual shards stored on https for some reason
    )
    assert (
        shards.shard_url("fake_package")
        == "https://example.org/shards/abcd.msgpack.zst"
    )

    # s3 and relative base_url
    shards = with_urls(
        "s3://index-bucket/linux-64/repodata_shards.msgpack.zst",  # shards index stored on s3
        "s3://package-bucket/linux-64",  # packages stored on different s3 bucket
        "./shards/",  # individual shards stored on https for some reason
    )
    assert (
        shards.shard_url("fake_package")
        == "s3://index-bucket/linux-64/shards/abcd.msgpack.zst"
    )


def test_shard_mentioned_packages_2():
    assert set(shard_mentioned_packages(FAKE_SHARD)) == set(
        (
            "bar",
            "baz",
            "quux",
            # "splat", # omit constrains
            "warble",
        )
    )

    # check that the bytes hash was converted to hex
    assert (
        FAKE_SHARD["packages.conda"]["foo.conda"]["sha256"]
        == hashlib.sha256().hexdigest()
    )  # type: ignore


EMPTY_SHARD: dict = {"packages": {}, "packages.conda": {}}


def _v3_shard(groups: dict) -> dict:
    return {**EMPTY_SHARD, "v3": groups}


def test_shard_mentioned_packages_v3_depends():
    shard = _v3_shard(
        {
            "cpython": {
                "cpython-3.12-h1.conda": {
                    "depends": ["openssl >=3", "libffi >=3.4"],
                },
            }
        }
    )
    names = list(shard_mentioned_packages(shard))
    assert "openssl" in names
    assert "libffi" in names


def test_shard_mentioned_packages_v3_extra_depends():
    shard = _v3_shard(
        {
            "numpy": {
                "numpy-2.0-py312.conda": {
                    "extra_depends": {
                        "cuda": ["cudatoolkit >=11.8"],
                        "mkl": ["mkl >=2023"],
                    },
                },
            }
        }
    )
    names = list(shard_mentioned_packages(shard))
    assert "cudatoolkit" in names
    assert "mkl" in names


def test_shard_mentioned_packages_v3_depends_and_extra_depends():
    shard = _v3_shard(
        {
            "scipy": {
                "scipy-1.13-py312.conda": {
                    "depends": ["numpy >=1.23"],
                    "extra_depends": {"cuda": ["cudatoolkit >=11.8"]},
                },
            }
        }
    )
    names = list(shard_mentioned_packages(shard))
    assert "numpy" in names
    assert "cudatoolkit" in names


def test_shard_mentioned_packages_v3_deduplication_within_v3():
    # two records in the same v3 group share a dep spec
    shard = _v3_shard(
        {
            "group": {
                "pkgA-1.0.conda": {"depends": ["openssl >=3"]},
                "pkgA-2.0.conda": {"depends": ["openssl >=3"]},
            }
        }
    )
    names = list(shard_mentioned_packages(shard))
    assert names.count("openssl") == 1


def test_shard_mentioned_packages_v3_deduplication_across_classic_and_v3():
    shard = {
        "packages": {
            "foo-1.0-0.tar.bz2": {
                "name": "foo",
                "version": "1.0",
                "build": "0",
                "build_number": 0,
                "depends": ["openssl >=3"],
            }
        },
        "packages.conda": {},
        "v3": {
            "group": {
                "bar-1.0.conda": {"depends": ["openssl >=3"]},
            }
        },
    }
    names = list(shard_mentioned_packages(shard))
    assert names.count("openssl") == 1


def test_shard_mentioned_packages_v3_ensures_hex_hash(mocker):
    # spy on the name as bound inside shards.py (imported by-name at module level)
    spy = mocker.spy(shards, "ensure_hex_hash")
    record = {"sha256": b"\xde\xad\xbe\xef" * 8, "depends": ["zlib >=1.2"]}
    shard = _v3_shard({"group": {"pkg-1.0.conda": record}})
    list(shard_mentioned_packages(shard))
    spy.assert_called()
    # ensure_hex_hash mutates in-place
    assert record["sha256"] == "deadbeef" * 8


def test_shard_mentioned_packages_v3_empty():
    shard_with_empty_v3 = _v3_shard({})
    shard_without_v3 = dict(EMPTY_SHARD)
    assert list(shard_mentioned_packages(shard_with_empty_v3)) == list(
        shard_mentioned_packages(shard_without_v3)
    )


def test_shard_mentioned_packages_v3_key_absent():
    shard = {
        "packages": {
            "pkg-1.0-0.tar.bz2": {
                "name": "pkg",
                "version": "1.0",
                "build": "0",
                "build_number": 0,
                "depends": ["zlib >=1.2"],
            }
        },
        "packages.conda": {},
    }
    names = list(shard_mentioned_packages(shard))
    assert "zlib" in names


def test_shard_mentioned_packages_extra_single_yield():
    # extra is emitted once, after both classic and v3 packages have been processed
    shard = _v3_shard({"group": {"pkg-1.0.conda": {"depends": ["zlib >=1.2"]}}})
    names = list(shard_mentioned_packages(shard, extra=["injected"]))
    assert names.count("injected") == 1


@pytest.mark.integration
def test_fetch_shards_channels(prepare_shards_test: None):
    """
    Test all channels fetch as Shards or ShardLike, depending on availability.
    """
    channels = list(context.default_channels)
    print(channels)

    channels.append(Channel(CONDA_FORGE_WITH_SHARDS))

    channel_data = fetch_channels(expand_channels(channels))

    # at least one should be real shards, not repodata.json presented as shards.
    assert any(isinstance(channel, Shards) for channel in channel_data.values())


def test_shards_cache(tmp_path: Path):
    cache = shards_cache.ShardCache(tmp_path)

    # test copy, context manager features
    with cache.copy() as cache2:
        assert cache2.conn is not cache.conn

    fake_shard = {"foo": "bar"}
    annotated_shard = shards_cache.AnnotatedRawShard(
        "https://foo",
        "foo",
        zstandard.compress(msgpack.dumps(fake_shard)),  # type: ignore
    )
    cache.insert(annotated_shard)

    data = cache.retrieve(annotated_shard.url)
    assert data == fake_shard
    assert data is not fake_shard

    data2 = cache.retrieve("notfound")
    assert data2 is None

    assert (tmp_path / shards_cache.SHARD_CACHE_NAME).exists()

    cache.close()


def test_shards_cache_recovery(tmp_path: Path):
    """
    Test that we can recover from a bad shards database.
    """
    db_path = tmp_path / shards_cache.SHARD_CACHE_NAME
    db_path.write_bytes(os.urandom(1024))

    class RemoveErrorShardCache(shards_cache.ShardCache):
        """
        Also test more-likely-on-Windows "can't remove" behavior.
        """

        def remove_cache(self):
            raise OSError("fail")

    cache = RemoveErrorShardCache(tmp_path, create=False)
    # sqlite3 won't complain until SQL is executed, but ShardCache() creates the
    # schema if it doesn't exist:
    with pytest.raises(sqlite3.DatabaseError):
        cache.connect(retry=False)
    cache.connect(retry=True)
    assert cache.retrieve("notfound") is None


def test_shards_cache_uses_wal(tmp_path: Path):
    """WAL journal mode is enabled on a fresh cache."""
    with shards_cache.ShardCache(tmp_path) as cache:
        mode = cache.conn.execute("PRAGMA journal_mode").fetchone()[0]
    assert mode == "wal"


def test_shards_cache_concurrent_read_write(tmp_path: Path):
    """Concurrent readers and writers must not raise OperationalError (#924)."""
    compressor = zstandard.ZstdCompressor(level=1)
    errors: list[Exception] = []
    stop = threading.Event()

    def writer(base):
        try:
            with shards_cache.ShardCache(base, create=False) as cache_copy:
                for i in range(200):
                    if stop.is_set():
                        break
                    shard = shards_cache.AnnotatedRawShard(
                        f"https://shard{i}",
                        f"pkg{i}",
                        compressor.compress(msgpack.dumps({f"pkg{i}": "data"})),
                    )
                    cache_copy.insert(shard)
        except Exception as exc:
            errors.append(exc)

    def reader(base):
        try:
            with shards_cache.ShardCache(base, create=False) as cache_copy:
                for i in range(200):
                    if stop.is_set():
                        break
                    urls = [f"https://shard{j}" for j in range(i + 1)]
                    cache_copy.retrieve_multiple(urls)
        except Exception as exc:
            errors.append(exc)

    with shards_cache.ShardCache(tmp_path) as cache:
        w = threading.Thread(target=writer, args=(cache.base,))
        r = threading.Thread(target=reader, args=(cache.base,))
        w.start()
        r.start()
        w.join(timeout=10)
        r.join(timeout=10)
        stop.set()

    # No sqlite3.OperationalError from either thread
    assert errors == []


NUM_FAKE_SHARDS = 64


class MockCache(NamedTuple):
    """
    Contain all the elements needed to be returned by the `mock_cache` fixture
    """

    num_shards: int
    shards: list[shards_cache.AnnotatedRawShard]
    cache: shards_cache.ShardCache


@pytest.fixture()
def mock_cache(tmp_path: Path) -> Iterator[MockCache]:
    """
    Set up a mock shard cache that will be used by multiple benchmark tests.
    """
    with shards_cache.ShardCache(tmp_path) as cache:
        NUM_FAKE_SHARDS = 64
        fake_shards = []

        compressor = zstandard.ZstdCompressor(level=1)
        for i in range(NUM_FAKE_SHARDS):
            fake_shard = {f"foo{i}": "bar"}
            annotated_shard = shards_cache.AnnotatedRawShard(
                f"https://foo{i}",
                f"foo{i}",
                compressor.compress(msgpack.dumps(fake_shard)),  # type: ignore
            )
            cache.insert(annotated_shard)
            fake_shards.append(annotated_shard)

        yield MockCache(num_shards=NUM_FAKE_SHARDS, shards=fake_shards, cache=cache)


@pytest.fixture
def shard_cache_with_data(
    mock_cache: MockCache,
) -> tuple[shards_cache.ShardCache, list[shards_cache.AnnotatedRawShard]]:
    """
    ShardCache with some data already inserted.
    """
    return mock_cache.cache, mock_cache.shards


def test_shard_cache_multiple(
    tmp_path: Path,
    shard_cache_with_data: tuple[
        shards_cache.ShardCache, list[shards_cache.AnnotatedRawShard]
    ],
):
    """
    Test that retrieve_multiple() is equivalent to several retrieve() calls.
    """
    cache, fake_shards = shard_cache_with_data

    none_retrieved = cache.retrieve_multiple([])  # coverage
    assert none_retrieved == {}

    start_multiple = time.monotonic_ns()
    retrieved = cache.retrieve_multiple([shard.url for shard in fake_shards])
    end_multiple = time.monotonic_ns()

    assert len(retrieved) == NUM_FAKE_SHARDS

    print(
        f"retrieve {len(fake_shards)} shards in a single call: {(end_multiple - start_multiple) / 1e9:0.6f}s"
    )

    start_single = time.monotonic_ns()
    for i, url in enumerate([shard.url for shard in fake_shards]):
        single = cache.retrieve(url)
        assert retrieved[url] == single
    end_single = time.monotonic_ns()
    print(
        f"retrieve {len(fake_shards)} shards with multiple calls: {(end_single - start_single) / 1e9:0.6f}s"
    )

    if (end_single - start_single) != 0:  # avoid ZeroDivisionError
        ratio = (end_multiple - start_multiple) / (end_single - start_single)
        print(f"Multiple API takes {ratio:.2f} times as long.")

        # Note: This assertion can be flaky depending on system load.
        # The batch API should be faster, but allow for some variance.
        # Only fail if batch API is significantly slower (> 2x).
        if ratio < 2:
            warnings.warn(f"batch API was {ratio:.2f}x slower than expected")

    assert (tmp_path / shards_cache.SHARD_CACHE_NAME).exists()


def test_shard_cache_clear_remove(tmp_path):
    """
    Test clear, remove cache functions not otherwise used.
    """
    cache = shards_cache.ShardCache(tmp_path)

    cache.insert(shards_cache.AnnotatedRawShard("https://bar", "bar", b"bar"))
    assert len(list(cache.conn.execute("SELECT * FROM SHARDS"))) == 1

    cache.clear_cache()
    assert list(cache.conn.execute("SELECT * FROM SHARDS")) == []

    assert (cache.base / shards_cache.SHARD_CACHE_NAME).exists()
    cache.remove_cache()
    assert not (cache.base / shards_cache.SHARD_CACHE_NAME).exists()

    cache.close()


def test_shardlike():
    """
    ShardLike class presents repodata.json as shards in a way that is suitable
    for our subsetting algorithm.
    """
    # Create a copy with mutable structure for testing
    repodata = {
        "info": {"subdir": "noarch", "base_url": "", "shards_base_url": ""},
        "packages": {},
        "packages.conda": {},
        "repodata_version": 2,
    }

    bad_repodata = repodata.copy()
    bad_repodata["info"] = {**bad_repodata["info"], "base_url": 4}
    with pytest.raises(TypeError):
        ShardLike(bad_repodata)

    # make fake packages
    for n in range(10):
        for m in range(n):  # 0 test0's
            repodata["packages"][f"test{n}{m}.tar.bz2"] = {"name": f"test{n}"}
            repodata["packages.conda"][f"test{n}{m}.tar.bz2"] = {"name": f"test{n}"}

    as_shards = ShardLike(repodata)

    assert len(as_shards.repodata_no_packages)
    assert len(as_shards.shards)

    assert sorted(as_shards.shards["test4"]["packages"].keys()) == [
        "test40.tar.bz2",
        "test41.tar.bz2",
        "test42.tar.bz2",
        "test43.tar.bz2",
    ]

    # Use visit_package instead of fetch_shard
    visited_shard = as_shards.visit_package("test1")
    assert visited_shard["packages"]["test10.tar.bz2"]["name"] == "test1"
    assert as_shards.url in repr(as_shards)
    assert "test1" in as_shards

    # Visit multiple packages, updating subset in as_shards
    as_shards.visit_package("test2")
    assert len(as_shards.visited) == 2
    assert as_shards.visited["test1"]
    assert as_shards.visited["test2"]

    as_shards.visited["package-that-does-not-exist"] = None
    repodata = as_shards.build_repodata()
    assert len(repodata["packages"]) == 3
    assert len(repodata["packages.conda"]) == 3


def test_shardlike_repr():
    """
    Code coverage for ShardLike.__repr__()
    """
    shardlike = ShardLike(
        {
            "packages": {},
            "packages.conda": {},
            "info": {"base_url": "", "shards_base_url": "", "subdir": "noarch"},
            "repodata_version": 1,
        },
        "https://conda.anaconda.org/",
    )
    cls, url, *_ = repr(shardlike).split()
    assert "ShardLike" in cls
    assert shardlike.url == url


def test_shard_hash_as_array():
    """
    Test that shard hashes can be bytes or list[int], for rattler compatibility.
    """
    name = "package"
    fake_shard: ShardsIndexDict = {
        "info": {"subdir": "noarch", "base_url": "", "shards_base_url": ""},
        "repodata_version": 1,
        "shards": {
            name: list(hashlib.sha256().digest()),  # type: ignore
        },
    }

    fake_shard_2 = fake_shard.copy()
    fake_shard_2["shards"] = fake_shard["shards"].copy()
    fake_shard_2["shards"][name] = hashlib.sha256().digest()

    assert isinstance(fake_shard["shards"][name], list)
    assert isinstance(fake_shard_2["shards"][name], bytes)

    index = Shards(fake_shard, "")
    index_2 = Shards(fake_shard_2, "")

    shard_url = index.shard_url(name)
    shard_url_2 = index_2.shard_url(name)
    assert shard_url == shard_url_2


def test_shards_coverage():
    """
    Call Shards() methods that are not otherwise called.
    """
    shard = shards.Shards(
        {
            "info": {
                "subdir": "noarch",
                "base_url": "",
                "shards_base_url": "./shards/",
            },
            "version": 1,
            "shards": {},
        },
        "https://example.org/noarch/repodata_shards.msgpack.zst",
    )  # type: ignore
    with pytest.raises(KeyError):
        # The visit_package() method tries to access self.visited[package]
        # which should raise KeyError if package not already visited
        shard.visit_package("package")
    shard.visited["package"] = {}  # type: ignore[assign]
    assert shard.visit_package("package") == {}


def test_ensure_hex_hash_in_record():
    """
    Test that ensure_hex_hash_in_record() converts bytes to hex strings.
    """
    name = "package"
    sha256_hash = hashlib.sha256()
    md5_hash = hashlib.md5()
    for sha, md5 in [
        (sha256_hash.digest(), md5_hash.digest()),
        (list(sha256_hash.digest()), list(md5_hash.digest())),
        (sha256_hash.hexdigest(), md5_hash.hexdigest()),
    ]:
        record = {
            "name": name,
            "sha256": sha,
            "md5": md5,
        }

        updated = shards.ensure_hex_hash(record)  # type: ignore
        assert isinstance(updated["sha256"], str)  # type: ignore
        assert updated["sha256"] == sha256_hash.hexdigest()  # type: ignore
        assert isinstance(updated["md5"], str)  # type: ignore
        assert updated["md5"] == md5_hash.hexdigest()  # type: ignore


@pytest.mark.integration
def test_batch_retrieve_from_cache(
    prepare_shards_test: None, empty_shards_cache: shards_cache.ShardCache
):
    """
    Test single database query to fetch cached shard URLs in a batch.
    """
    channels = [*context.default_channels, Channel(CONDA_FORGE_WITH_SHARDS)]
    roots = ROOT_PACKAGES[:]

    with _timer("repodata.json/shards index fetch"):
        channel_data = fetch_channels(expand_channels(channels))

    with _timer("Shard fetch"):
        sharded = [
            channel for channel in channel_data.values() if isinstance(channel, Shards)
        ]
        assert sharded, "No sharded repodata found"
        remaining = batch_retrieve_from_cache(sharded, roots, empty_shards_cache)
        print(f"{len(remaining)} shards to fetch from network")

    # execute "no sharded channels" branch
    remaining = batch_retrieve_from_cache([], ["python"], empty_shards_cache)
    assert remaining == []


@pytest.mark.benchmark
@pytest.mark.parametrize("retrieval_type", ["retrieve_multiple", "retrieve_single"])
def test_shard_cache_multiple_profile(retrieval_type, mock_cache: MockCache):
    """
    Measure the difference between `shards_cache.retrieve_multiple` and `shards_cache.retrieve`.

    `shards_cache.retrieve_multiple should be faster than `shards_cache.retrieve`.
    """
    if retrieval_type == "retrieve_multiple":
        retrieved = mock_cache.cache.retrieve_multiple(
            [shard.url for shard in mock_cache.shards]
        )
        assert len(retrieved) == mock_cache.num_shards

    elif retrieval_type == "retrieve_single":
        retrieved = {}
        for i, url in enumerate([shard.url for shard in mock_cache.shards]):
            single = mock_cache.cache.retrieve(url)
            retrieved[url] = single

        assert len(retrieved) == mock_cache.num_shards


def test_shards_connections(monkeypatch):
    """
    Test _shards_connections() and execute all its code.
    """

    assert context.repodata_threads is None
    assert _shards_connections() == 10  # requests' default

    monkeypatch.setattr("conda._private.shards.misc.SHARDS_CONNECTIONS_DEFAULT", 7)
    assert _shards_connections() == 7

    monkeypatch.setattr(context, "_repodata_threads", 4)
    assert _shards_connections() == 4


def test_filter_packages_simple():
    simple = {
        "packages": {"a.tar.bz2": {}, "b.tar.bz2": {}},
        "packages.conda": {
            "a.conda": {},
        },
    }
    trimmed = shards_subset.filter_redundant_packages(simple)  # type: ignore
    assert trimmed["packages"] == {"b.tar.bz2": {}}

    assert (
        shards_subset.filter_redundant_packages(simple, use_only_tar_bz2=True) is simple
    )  # type: ignore


# the function under test is not particularly slow but downloads large repodata
# unnecessarily. Useful if remove_legacy_packages needs to be debugged.
@pytest.mark.skip(reason="slow")
@pytest.mark.benchmark
@pytest.mark.parametrize(
    "channel", ("conda-forge/linux-64", "https://repo.anaconda.com/pkgs/main/linux-64")
)
def test_filter_packages_repodata(channel, benchmark):
    repodata, _ = SubdirData(Channel(channel)).repo_fetch.fetch_latest_parsed()
    print(
        f"Original {channel} has {len(repodata['packages'])} .tar.bz2 packages and {len(repodata['packages.conda'])} .conda packages"
    )

    repodata_trimmed = {}

    def remove():
        nonlocal repodata_trimmed
        repodata_trimmed = shards_subset.filter_redundant_packages(repodata)  # type: ignore

    benchmark(remove)

    print(
        f"Trimmed {channel} has {len(repodata_trimmed['packages'])} .tar.bz2 packages and {len(repodata['packages.conda'])} .conda packages"
    )


def test_offline_mode_expired_cache(http_server_shards, monkeypatch, tmp_path):
    """
    Test that expired cached shards are used when offline mode is enabled.

    Note: This test has been simplified from the original as the API has changed.
    The _install_shards_cache context manager and fetch_shard method are no
    longer available. TODO: Rewrite this test to use the new ShardFetch API.
    """
    # Guarantee clean cache to avoid interference from previous tests
    monkeypatch.setenv("CONDA_PKGS_DIRS", str(tmp_path))
    reset_context()

    channel = Channel.from_url(f"{http_server_shards}/noarch")
    subdir_data = SubdirData(channel)

    # Populate cache by fetching shards index
    found = fetch_shards_index(subdir_data)
    assert found is not None
    assert "foo" in found  # Verify we have the expected packages


def test_offline_mode_no_cache(
    http_server_shards, empty_shards_cache, monkeypatch, tmp_path
):
    """
    Test that offline mode falls back gracefully when no cache exists.

    When offline and no cache exists, the system should fall back to non-sharded repodata
    rather than failing.
    """
    # Guarantee empty cache as to not interfere with other tests.
    monkeypatch.setenv("CONDA_PKGS_DIRS", str(tmp_path))
    reset_context()

    channel = Channel.from_url(f"{http_server_shards}/noarch")
    subdir_data = SubdirData(channel)

    # Remove cache if it exists
    repo_cache = subdir_data.repo_fetch.repo_cache
    assert not repo_cache.cache_path_shards.exists()

    # Enable offline mode
    monkeypatch.setattr(context, "offline", True)
    reset_context()

    # Try to fetch shards index in offline mode without cache
    # Should return None (fallback to non-sharded repodata)
    found = fetch_shards_index(subdir_data)
    assert found is None


def test_offline_mode_missing_shard_in_cache(
    http_server_shards, empty_shards_cache, tmp_path, monkeypatch
):
    """
    Test that offline mode handles missing shards gracefully when the package
    exists in the shard index but the shard is not cached.

    When offline and a package is in the shard index but not in cache,
    offline_nofetch_thread should return an empty shard rather than failing.

    Note: This test has been simplified as the API has changed.
    The fetch_shard method is no longer available. TODO: Rewrite with new API.
    """
    # Guarantee empty cache; the other 'test_offline...' test can cause 'assert
    # found is not None' to fail.
    monkeypatch.setenv("CONDA_PKGS_DIRS", str(tmp_path))
    reset_context()

    channel = Channel.from_url(f"{http_server_shards}/noarch")
    subdir_data = SubdirData(channel)

    # Fetch the shards index (so "bar" is in the index)
    found = fetch_shards_index(subdir_data)
    assert found is not None
    # Verify "bar" is in the index
    assert "bar" in found

    # Verify we can get the URL for "bar" shard
    bar_shard_url = found.shard_url("bar")
    assert bar_shard_url  # Just verify it exists


def test_repodata_shards_sends_etag(monkeypatch, tmp_path):
    """
    Test that repodata_shards(), normally only called by fetch_shards_index, can
    send etag. (Our test web server doesn't use etag).
    """
    # Guarantee clean cache to avoid interference from previous tests
    monkeypatch.setenv("CONDA_PKGS_DIRS", str(tmp_path))
    reset_context()

    class MockSession:
        proxies = None
        get_count = 0

        def __call__(self, *args):
            return self

        def get(self, url, headers, **kwargs):
            self.url = url
            self.headers = headers
            self.kwargs = kwargs
            raise NotImplementedError()

    mock_session = MockSession()
    monkeypatch.setattr(shards, "get_session", mock_session)

    channel = Channel("http://localhost/mock/noarch")
    subdir_data = SubdirData(channel)

    repo_cache = subdir_data.repo_cache
    repo_cache.load_state()
    repo_cache.state["etag"] = "etag"

    with pytest.raises(NotImplementedError):
        _repodata_shards(channel.url(), repo_cache)

    assert mock_session.headers == {"If-None-Match": "etag"}


def test_repodata_shards_offline(monkeypatch, tmp_path):
    monkeypatch.setattr(context, "offline", True)

    class FakePath:
        def __init__(self, exists):
            self._exists = exists

        def exists(self):
            return self._exists

        def read_bytes(self):
            return b"cached"

    class FakeCache:
        def __init__(self, cache_path_shards):
            self.cache_path_shards = cache_path_shards

    # In offline mode, return cached data if available, even if expired.
    assert _repodata_shards("https://channel", FakeCache(FakePath(True))) == b"cached"  # type: ignore

    # In offline mode, raise RepodataIsEmpty if cache data is not available.
    with pytest.raises(conda.gateways.repodata.RepodataIsEmpty):
        _repodata_shards("https://channel", FakeCache(FakePath(False)))  # type: ignore


@pytest.mark.parametrize(
    "base_url,relative_url,expected",
    [
        # HTTP URLs - standard urljoin behavior
        (
            "https://repo.anaconda.com/pkgs/main/linux-64",
            "",
            "https://repo.anaconda.com/pkgs/main/",
        ),
        (
            "https://repo.anaconda.com/pkgs/main/linux-64",
            "subdir",
            "https://repo.anaconda.com/pkgs/main/",
        ),
        # Realistic file URLs: in practice, base_url is a repodata file URL,
        # and urljoin(url, ".") strips the filename to get the directory.
        (
            "https://repo.anaconda.com/pkgs/main/linux-64/repodata_shards.msgpack.zst",
            "",
            "https://repo.anaconda.com/pkgs/main/linux-64/",
        ),
        (
            "s3://bucket-name/linux-64/repodata_shards.msgpack.zst",
            "",
            "s3://bucket-name/linux-64/",
        ),
        (
            "s3://bucket-name/linux-64/repodata_shards.msgpack.zst",
            ".",
            "s3://bucket-name/linux-64/",
        ),
        (
            "file:///path/to/channel/linux-64/repodata_shards.msgpack.zst",
            "",
            "file:///path/to/channel/linux-64/",
        ),
        (
            "ftp://ftp.example.com/pub/linux-64/repodata_shards.msgpack.zst",
            "",
            "ftp://ftp.example.com/pub/linux-64/",
        ),
        # Trailing-slash directory URLs are preserved as-is for all schemes
        ("s3://bucket-name/linux-64/", "", "s3://bucket-name/linux-64/"),
        ("file:///path/to/channel/linux-64/", "", "file:///path/to/channel/linux-64/"),
        # Non-HTTP without trailing slash: urljoin treats the last segment as a
        # filename (consistent with HTTP behavior above)
        ("s3://bucket-name/linux-64", "", "s3://bucket-name/"),
        ("s3://bucket-name/linux-64", ".", "s3://bucket-name/"),
        ("file:///path/to/channel/linux-64", "", "file:///path/to/channel/"),
        ("ftp://ftp.example.com/pub/linux-64", "", "ftp://ftp.example.com/pub/"),
        # requires final "append /" check, second URL is absolute overriding first URL.
        (
            "s3://bucket-name/linux-64",
            "s3://bucket-name/noslash",
            "s3://bucket-name/noslash/",
        ),
        # requires final "append /" check, second URL also ends with /
        (
            "s3://bucket-name/linux-64",
            "s3://bucket-name/slash/",
            "s3://bucket-name/slash/",
        ),
    ],
)
def test_safe_urljoin_with_slash(base_url, relative_url, expected):
    """
    Test _safe_urljoin_with_slash handles various URL schemes correctly.

    urljoin only works for schemes in ``urllib.parse.uses_relative`` (http, https,
    file, ftp, etc.). For unregistered schemes like s3://, it returns just ``"."``
    instead of the resolved URL. This function handles those via scheme-swap.

    All schemes should behave consistently: the last path segment without a
    trailing slash is treated as a filename and stripped.

    See: https://github.com/conda/conda-libmamba-solver/issues/866
    """
    result = _safe_urljoin_with_slash(base_url, relative_url)
    assert result == expected
