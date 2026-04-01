# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (C) 2022 Anaconda, Inc
# Copyright (C) 2023 conda
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
import time
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple

import msgpack
import pytest
import zstandard
from requests import Request, Response

import conda.gateways.repodata
from conda.base.context import context, reset_context
from conda.core.subdir_data import SubdirData
from conda.gateways.repodata.shards import (
    RepodataSubset,
    ShardLike,
    Shards,
    batch_retrieve_from_cache,
    fetch_channels,
    fetch_shards_index,
    filter_redundant_packages,
    shard_mentioned_packages,
)
from conda.gateways.repodata.shards import cache as shards_cache
from conda.gateways.repodata.shards import core as shards_core
from conda.gateways.repodata.shards import (
    ensure_hex_hash as ensure_hex_hash_record,
)
from conda.gateways.repodata.shards import subset as shards_subset_mod
from conda.gateways.repodata.shards.core import (
    _repodata_shards,
    _safe_urljoin_with_slash,
    _shards_connections,
)
from conda.models.channel import Channel
from conda.testing import http_test_server

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Iterator

    from conda.gateways.repodata.shards.typing import ShardDict, ShardsIndexDict

HERE = Path(__file__).parent

# was conda-forge-sharded during testing
CONDA_FORGE_WITH_SHARDS = "conda-forge"

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


def package_names(shard: ShardDict):
    """
    All package names mentioned in a shard (should be a single package name)
    """
    return set(package["name"] for package in shard["packages"].values()) | set(
        package["name"] for package in shard["packages.conda"].values()
    )


def expand_channels(channels: list[Channel], subdirs: Iterable[str] | None = None):
    """
    Expand channels list into a dict of subdir-aware channels, matching
    LibMambaIndexHelper / solver index behavior.
    """
    subdirs_ = list(context.subdirs) if subdirs is None else subdirs
    urls = {}
    seen_noauth = set()
    channels_with_subdirs = []
    for channel in channels:
        for url in channel.urls(with_credentials=True, subdirs=subdirs_):
            channels_with_subdirs.append(Channel(url))
    for channel in channels_with_subdirs:
        noauth_urls = [
            url
            for url in channel.urls(with_credentials=False)
            if url.endswith(channel.subdir)
        ]
        if seen_noauth.issuperset(noauth_urls):
            continue
        auth_urls = [
            url.replace(" ", "%20")
            for url in channel.urls(with_credentials=True)
            if url.endswith(tuple(subdirs_))
        ]
        if noauth_urls != auth_urls:
            urls.update({url: channel for url in auth_urls})
            seen_noauth.update(noauth_urls)
            continue
        for url in noauth_urls:
            if url not in seen_noauth:
                urls[url] = channel
                seen_noauth.add(url)
    encoded: dict[str, Channel] = {}
    for url, ch in urls.items():
        if url.startswith("file://"):
            url = url.replace(" ", "%20")
        encoded[url] = ch
    return encoded


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


@pytest.fixture
def prepare_shards_test(monkeypatch: pytest.MonkeyPatch):
    """
    Reset token to avoid being logged in. e.g. the testing channel doesn't understand them.
    Enable shards.
    """
    logging.basicConfig(level=logging.INFO)
    from conda.gateways.repodata.shards import cache, core, subset

    for module in (core, cache, subset):
        module.log.setLevel(logging.DEBUG)

    monkeypatch.setenv("CONDA_TOKEN", "")
    monkeypatch.setenv("CONDA_PLUGINS_USE_SHARDED_REPODATA", "1")
    reset_context()
    assert context.plugins.use_sharded_repodata is True


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


def repodata_deep_hex_hashes(repodata: dict):
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

        http = http_test_server.run_test_server(
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
    monkeypatch.setattr(shards_core, "get_session", mock_session)

    channel = Channel("http://localhost/mock/noarch")
    subdir_data = SubdirData(channel)

    repo_cache = subdir_data.repo_cache
    repo_cache.load_state()
    assert repo_cache.state.should_check_format("shards")

    fetch_shards_index(subdir_data, None)

    # load json directly due to issues with repo_cache API, also
    # fetch_shards_index gets a different repo_cache instance:
    repo_cache.state.update(json.loads(repo_cache.cache_path_state.read_text()))
    assert repo_cache.state.should_check_format("shards") == expect_should_check_shards
    assert mock_session.get_count == 1

    # assert that retry skips over shards without trying to GET
    get_count = mock_session.get_count
    second_try = fetch_shards_index(subdir_data, None)
    assert second_try is None
    assert mock_session.get_count == get_count + expect_should_check_shards


def test_fetch_shards_error(http_server_shards, empty_shards_cache):
    channel = Channel.from_url(f"{http_server_shards}/noarch")
    subdir_data = SubdirData(channel)
    found = fetch_shards_index(subdir_data, empty_shards_cache)
    assert found

    not_found = fetch_shards_index(
        SubdirData(Channel.from_url(f"{http_server_shards}/linux-64")),
        empty_shards_cache,
    )
    assert not not_found

    # cover "unexpected package name in shard" branch
    found.visited.clear()
    assert "packages" in found.fetch_shard("wrong_package_name")

    # one non-error shard
    shard_a = found.fetch_shard("foo")
    shard_b = found.fetch_shard("foo")
    assert shard_a is shard_b
    found.visited.clear()  # force sqlite3 cache usage
    shard_c = found.fetch_shard("foo")
    assert shard_a is not shard_c
    assert shard_a == shard_c

    with pytest.raises(conda.gateways.repodata.RepodataIsEmpty):
        found.fetch_shard("fake_package")

    # currently logs KeyError: 'packages', doesn't cache, returns decoded msgpack
    malo = found.fetch_shard("malformed")
    assert malo == {"follows_schema": False}  # XXX should we return None or raise

    with pytest.raises(zstandard.ZstdError):
        found.fetch_shard("not_zstd")

    # unclear if all possible "bad msgpack" errors inherit from a common class
    # besides ValueError
    with pytest.raises(ValueError):
        found.fetch_shard("not_msgpack")


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
            None,  # type: ignore
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

    cache = shards_cache.ShardCache(tmp_path, create=False)
    # sqlite3 won't complain until SQL is executed, but ShardCache() creates the
    # schema if it doesn't exist:
    with pytest.raises(sqlite3.DatabaseError):
        cache.connect(retry=False)
    cache.connect(retry=True)
    assert cache.retrieve("notfound") is None


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
        print(
            f"Multiple API takes {(end_multiple - start_multiple) / (end_single - start_single):.2f} times as long."
        )

        assert (end_multiple - start_multiple) / (end_single - start_single) < 1, (
            "batch API took longer"
        )

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
    repodata = json.loads(
        (HERE / "data" / "mamba_repo" / "noarch" / "repodata.json").read_text()
    )

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

    fetched_shard = as_shards.fetch_shard("test1")
    assert fetched_shard["packages"]["test10.tar.bz2"]["name"] == "test1"
    assert as_shards.url in repr(as_shards)
    assert "test1" in as_shards

    fetched_shards = as_shards.fetch_shards(("test1", "test2"))
    assert len(fetched_shards) == 2
    assert fetched_shards["test1"]
    assert fetched_shards["test2"]

    as_shards.visited.update(fetched_shards)
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

    index = Shards(fake_shard, "", None)  # type: ignore
    index_2 = Shards(fake_shard_2, "", None)  # type: ignore

    shard_url = index.shard_url(name)
    shard_url_2 = index_2.shard_url(name)
    assert shard_url == shard_url_2


def test_shards_coverage():
    """
    Call Shards() methods that are not otherwise called.
    """
    shard = Shards(
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
        # The visit_shard() method is used for ShardLike (from monolithic
        # repodata) and makes a package part of the generated repodata. For
        # Shards() (from sharded repodata), we assign directly to visited and
        # don't wind up calling visit_shard().
        shard.visit_package("package")
    shard.visited["package"] = {}  # type: ignore[assign]
    assert shard.visit_package("package") == {}

    assert shard.shards_cache is None
    with pytest.raises(ValueError, match="shards_cache"):
        shard._process_fetch_result(None, None, None, None)


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

        updated = ensure_hex_hash_record(record)  # type: ignore
        assert isinstance(updated["sha256"], str)  # type: ignore
        assert updated["sha256"] == sha256_hash.hexdigest()  # type: ignore
        assert isinstance(updated["md5"], str)  # type: ignore
        assert updated["md5"] == md5_hash.hexdigest()  # type: ignore


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
        for shard in sharded:
            shard.shards_cache = empty_shards_cache
        assert sharded, "No sharded repodata found"
        remaining = batch_retrieve_from_cache(sharded, roots)
        print(f"{len(remaining)} shards to fetch from network")

    # execute "no sharded channels" branch
    remaining = batch_retrieve_from_cache([], ["python"])
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

    monkeypatch.setattr(shards_core, "SHARDS_CONNECTIONS_DEFAULT", 7)
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
    trimmed = filter_redundant_packages(simple)  # type: ignore
    assert trimmed["packages"] == {"b.tar.bz2": {}}

    assert filter_redundant_packages(simple, use_only_tar_bz2=True) is simple  # type: ignore


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
        repodata_trimmed = filter_redundant_packages(repodata)  # type: ignore

    benchmark(remove)

    print(
        f"Trimmed {channel} has {len(repodata_trimmed['packages'])} .tar.bz2 packages and {len(repodata['packages.conda'])} .conda packages"
    )


def test_offline_mode_expired_cache(http_server_shards, monkeypatch, tmp_path):
    """
    Test that expired cached shards are used when offline mode is enabled.
    """
    # Guarantee clean cache to avoid interference from previous tests
    monkeypatch.setenv("CONDA_PKGS_DIRS", str(tmp_path))
    reset_context()

    channel = Channel.from_url(f"{http_server_shards}/noarch")
    subdir_data = SubdirData(channel)

    # Populate cache
    found = fetch_shards_index(subdir_data, None)
    assert found is not None

    # Fetch a shard to populate the sqlite3 cache. Install shards cache, since found will have None cache.
    with shards_subset_mod._install_shards_cache([found]):
        found.fetch_shard("foo")

    repo_cache = subdir_data.repo_fetch.repo_cache
    assert repo_cache.cache_path_shards.exists()

    # Make cache stale by setting refresh_ns to 1 day ago
    cache_state = repo_cache.state
    cache_state["refresh_ns"] = time.time_ns() - (24 * 60 * 60 * 1_000_000_000)

    # Persist stale timestamp
    with repo_cache.lock("r+") as state_file:
        state_file.seek(0)
        state_file.truncate()
        state_dict = dict(cache_state)
        json.dump(state_dict, state_file)

    assert repo_cache.stale()

    # Enable offline mode
    monkeypatch.setattr(context, "offline", True)
    reset_context()

    found_offline = fetch_shards_index(subdir_data, None)
    assert found_offline is not None

    subset = RepodataSubset([found_offline])
    subset.reachable_pipelined(("foo",))
    repodata = found_offline.build_repodata()
    assert len(repodata["packages"]) + len(repodata["packages.conda"]) > 0, (
        "no package records"
    )


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
    found = fetch_shards_index(subdir_data, empty_shards_cache)
    assert found is None


def test_offline_mode_missing_shard_in_cache(
    http_server_shards, empty_shards_cache, tmp_path, monkeypatch
):
    """
    Test that offline mode handles missing shards gracefully when the package
    exists in the shard index but the shard is not cached.

    When offline and a package is in the shard index but not in cache,
    offline_nofetch_thread should return an empty shard rather than failing.
    """
    # Guarantee empty cache; the other 'test_offline...' test can cause 'assert
    # found is not None' to fail.
    monkeypatch.setenv("CONDA_PKGS_DIRS", str(tmp_path))
    reset_context()

    channel = Channel.from_url(f"{http_server_shards}/noarch")
    subdir_data = SubdirData(channel)

    # Fetch the shards index (so "bar" is in the index)
    found = fetch_shards_index(subdir_data, empty_shards_cache)
    assert found is not None
    # Verify "bar" is in the index
    assert "bar" in found

    # Fetch "foo" shard to ensure cache exists, but don't fetch "bar"
    found.fetch_shard("foo")

    # Verify "bar" shard is not in the cache
    bar_shard_url = found.shard_url("bar")
    cache = shards_cache.ShardCache(Path(conda.gateways.repodata.create_cache_dir()))
    assert cache.retrieve(bar_shard_url) is None, "bar shard should not be in cache"

    # Enable offline mode
    monkeypatch.setattr(context, "offline", True)
    reset_context()

    # Fetch shards index again in offline mode (should use cached index)
    found_offline = fetch_shards_index(subdir_data, empty_shards_cache)
    assert found_offline is not None

    # Try to reach "bar" which is in index but not in cache
    # In offline mode, this should return an empty shard gracefully
    subset = RepodataSubset([found_offline])
    subset.reachable_pipelined(("bar",))

    # Build repodata - should complete without crashing
    repodata = found_offline.build_repodata()
    # The repodata may be empty since "bar" is not cached and returns empty shard
    assert isinstance(repodata, dict)


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
    monkeypatch.setattr(shards_core, "get_session", mock_session)

    channel = Channel("http://localhost/mock/noarch")
    subdir_data = SubdirData(channel)

    repo_cache = subdir_data.repo_cache
    repo_cache.load_state()
    repo_cache.state["etag"] = "etag"

    with pytest.raises(NotImplementedError):
        _repodata_shards(channel.url(), repo_cache)

    assert mock_session.headers == {"If-None-Match": "etag"}


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
