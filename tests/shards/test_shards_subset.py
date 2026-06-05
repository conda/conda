# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import concurrent.futures
import json
import queue
import random
import threading
import time
import urllib.parse
from contextlib import suppress
from pathlib import Path
from queue import Empty, SimpleQueue
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
from requests.exceptions import HTTPError

import conda.gateways.repodata
from conda._private.shards import cache as shards_cache
from conda._private.shards import subset as shards_subset
from conda._private.shards.shards import (
    ShardLike,
    Shards,
    fetch_channels,
    fetch_shards_index,
    shard_mentioned_packages,
)
from conda._private.shards.subset import (
    QUEUE_TIMEOUT,
    NodeId,
    RepodataSubset,
    build_repodata_subset,
    combine_batches_until_none,
    exception_to_queue,
    filter_redundant_packages,
)
from conda.base.context import context, reset_context
from conda.common.compat import on_win
from conda.core.subdir_data import SubdirData
from conda.models.channel import Channel

from .conftest import (
    CONDA_FORGE_WITH_SHARDS,
    FAKE_REPODATA,
    ROOT_PACKAGES,
    _timer,
    ensure_hex_hash,
    expand_channels,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from pytest_benchmark.plugin import BenchmarkFixture

    from conda._private.shards.typing import ShardDict
    from conda.testing.fixtures import CondaCLIFixture


# avoid underscores in names to parse them easily
TESTING_SCENARIOS = [
    {
        "name": "python",
        "packages": ["python"],
        "prefetch_packages": [],
        "channel": CONDA_FORGE_WITH_SHARDS,
        "platform": "linux-64",
    },
    {
        "name": "data_science_ml",
        "packages": ["scikit-learn", "matplotlib"],
        "prefetch_packages": ["python", "numpy"],
        "channel": CONDA_FORGE_WITH_SHARDS,
        "platform": "linux-64",
    },
    {
        "name": "web_development",
        "packages": ["django", "celery"],
        "prefetch_packages": ["python", "requests"],
        "channel": CONDA_FORGE_WITH_SHARDS,
        "platform": "linux-64",
    },
    {
        "name": "scientific_computing",
        "packages": ["scipy", "sympy", "pytorch"],
        "prefetch_packages": ["python", "numpy", "pandas"],
        "channel": CONDA_FORGE_WITH_SHARDS,
        "platform": "linux-64",
    },
    {
        "name": "devops_automation",
        "packages": ["ansible", "pyyaml", "jinja2"],
        "prefetch_packages": ["python"],
        "channel": CONDA_FORGE_WITH_SHARDS,
        "platform": "linux-64",
    },
    {
        "name": "vaex",
        "packages": ["vaex"],
        "prefetch_packages": ["python", "numpy", "pandas"],
        "channel": CONDA_FORGE_WITH_SHARDS,
        "platform": "linux-64",
    },
]

if True:  # one fast, one slow-ish scenario for faster tests unless debugging.
    TESTING_SCENARIOS = [
        scenario
        for scenario in TESTING_SCENARIOS
        if scenario["name"] in ("python", "devops_automation")
    ]


@pytest.mark.integration
@pytest.mark.parametrize(
    "root_packages", [ROOT_PACKAGES[:] + ["vaex"], []], ids=["complex", "empty"]
)
def test_build_repodata_subset_pipelined(
    prepare_shards_test: None, root_packages: list[str], tmp_path
):
    """
    Build repodata subset using a worker threads dependency traversal algorithm.

    This is the minimal pipelined test adapted from conda-libmamba-solver.
    """
    channels = []
    channels.append(Channel(CONDA_FORGE_WITH_SHARDS))

    with _timer("fetch_channels()"):
        channel_data = fetch_channels(expand_channels(channels))

    def assert_quick(ns: int):
        # Check that the 1 second queue timeout doesn't happen on an empty
        # traversal.
        if not root_packages:
            assert (ns / 1e9) < 0.2, "Empty shard traversal should be quick."

    with _timer("RepodataSubset.reachable_pipelined()", assert_quick):
        subset = RepodataSubset((*channel_data.values(),))
        subset.reachable_pipelined(root_packages)
        print(f"{subset.node_count} (channel, package) nodes discovered")

    print(
        "Channels:",
        ",".join(urllib.parse.urlparse(url).path[1:] for url in channel_data),
    )


@pytest.mark.parametrize("algorithm", ["bfs", "pipelined"])
def test_build_repodata_subset_local_server(
    http_server_shards, algorithm, monkeypatch, tmp_path
):
    """
    Ensure we can fetch and build a valid repodata subset from our mock local server.
    """
    # Guarantee clean cache to avoid interference from previous tests
    monkeypatch.setenv("CONDA_PKGS_DIRS", str(tmp_path))
    reset_context()

    channel = Channel.from_url(f"{http_server_shards}/noarch")
    root_packages = ["foo"]

    expected_repodata = ensure_hex_hash(FAKE_REPODATA)
    expected_repodata = filter_redundant_packages(expected_repodata)  # type: ignore

    channel_data = build_repodata_subset(
        root_packages, {channel.url() or "": channel}, algorithm=algorithm
    )

    for shardlike in channel_data.values():
        # expanded in fetch_channels() "channel.urls(True, context.subdirs)"
        if "/noarch/" not in shardlike.url:
            continue
        actual_repodata = shardlike.build_repodata()

        assert actual_repodata == expected_repodata, (
            "actual",
            actual_repodata,
            "expected",
            expected_repodata,
        )


def test_build_repodata_subset_no_shards(http_server_shards):
    """
    If no channel has repodata_shards.msgpack.zst, build_repodata_subset()
    returns None.
    """
    channels = expand_channels([Channel(http_server_shards + "/notfound")])
    assert build_repodata_subset([], channels) is None


@pytest.mark.integration
def test_build_repodata_subset(prepare_shards_test: None, tmp_path):
    """
    Build repodata subset and compute the size if it was serialized as repodata.json.
    """
    import json

    # installed, plus what we want to add (twine)
    root_packages = ROOT_PACKAGES[:]

    channels = list(context.default_channels)
    channels.append(Channel(CONDA_FORGE_WITH_SHARDS))
    channel_dict = expand_channels(channels)

    with _timer("build_repodata_subset()"):
        channel_data = build_repodata_subset(root_packages, channel_dict)
        assert channel_data  # would return None if no shards on any channel

    # Measure size
    repodata_size = 0
    for _, shardlike in channel_data.items():
        repodata = shardlike.build_repodata()
        repodata_text = json.dumps(
            repodata,
            indent=0,
            separators=(",", ":"),
            sort_keys=True,
            ensure_ascii=False,
        )
        repodata_size += len(repodata_text.encode("utf-8"))

    assert channel_data and len(channel_data), "no channel data"
    print(f"Repodata subset would be {repodata_size} bytes as json")

    print(
        "Channels:",
        ",".join(urllib.parse.urlparse(url).path[1:] for url in channel_data),
    )


@pytest.mark.parametrize(
    "algorithm,depth,root_package,expected_result",
    [
        (
            "bfs",
            0,
            "bar",
            {
                "bar",
            },
        ),
        (
            "pipelined",
            0,
            "bar",
            {
                "bar",
            },
        ),
        (
            "bfs",
            1,
            "bar",
            {
                "bar",
                "foo",
            },
        ),
        ("pipelined", 1, "bar", {"bar", "foo"}),
        (
            "bfs",
            10,
            "foo",
            {
                "bar",
                "foo",
            },
        ),
        ("pipelined", 10, "foo", {"bar", "foo"}),
    ],
)
def test_build_repodata_subset_with_depth(
    http_server_shards,
    algorithm,
    depth,
    root_package,
    expected_result,
    monkeypatch,
    tmp_path,
):
    """
    Ensure we can fetch and build a valid repodata subset for different fetch depths from our mock local server.
    A depth of 0 should just get the root package. Depth of 1 should get just the just the first level dependencies, etc,
    """
    # Guarantee clean cache to avoid interference from previous tests
    monkeypatch.setenv("CONDA_PKGS_DIRS", str(tmp_path))
    reset_context()

    channel = Channel.from_url(f"{http_server_shards}/noarch")
    channel_data = build_repodata_subset(
        [root_package], {channel.url() or "": channel}, algorithm=algorithm, depth=depth
    )

    record_names = []
    for shardlike in channel_data.values():
        record_names += [rec.get("name") for _, rec in shardlike.iter_records_v3()]
    assert set(record_names) == expected_result


@pytest.mark.parametrize(
    "search_spec,should_find_results",
    [
        pytest.param("foo", True, id="exact_foo"),
        pytest.param("bar", True, id="exact_bar"),
        pytest.param("bar*", True, id="wild_bar*"),
        pytest.param("bar 1 0_a", True, id="bar_params_match"),
        pytest.param("bar[sha256=a]", False, id="params_nomatch"),
        pytest.param("xyz", False, id="exact_no_match"),
        pytest.param("*", False, id="bare *"),
    ],
)
def test_query_all_sharded_search(
    http_server_shards,
    search_spec,
    should_find_results,
    monkeypatch,
    tmp_path,
):
    """
    Test that query_all can search for packages against sharded repodata.
    """
    from conda.core.subdir_data import query_all
    from conda.models.match_spec import MatchSpec

    # Enable shards and clean cache
    monkeypatch.setenv("CONDA_REPODATA_USE_SHARDS", "true")
    monkeypatch.setenv("CONDA_PKGS_DIRS", str(tmp_path))
    reset_context()

    channel = Channel.from_url(f"{http_server_shards}/noarch")
    spec = MatchSpec(search_spec)

    if search_spec == "*":
        with pytest.raises(ValueError, match="bare '*'"):
            query_all(spec, [channel], subdirs=["noarch"])
        return

    results = query_all(spec, [channel], subdirs=["noarch"])

    if should_find_results:
        assert len(results) > 0, f"Expected to find packages for {search_spec}"
        # Verify all results match the spec
        for result in results:
            assert spec.match(result), f"{result.name} doesn't match {spec}"
    else:
        assert len(results) == 0, (
            f"Expected no results for {search_spec}, but found {results}"
        )


class TestAddPipAsPythonDependency:
    """Tests for add_pip_as_python_dependency context setting"""

    def test_add_pip_as_python_dependency_context(self):
        """Test that add_pip_as_python_dependency context setting exists"""
        # Just verify the context attribute exists
        assert hasattr(context, "add_pip_as_python_dependency")
        # Should be a boolean
        result = context.add_pip_as_python_dependency
        assert isinstance(result, bool)

    def test_add_pip_as_python_dependency_in_shardlike(self):
        """Test that ShardLike correctly handles python package with pip dependency"""
        repodata = {
            "info": {"base_url": ""},
            "packages": {
                "python-3.10.0-h1234567_0.tar.bz2": {
                    "name": "python",
                    "version": "3.10.0",
                    "build": "h1234567_0",
                    "build_number": 0,
                    "depends": [],
                }
            },
            "packages.conda": {},
            "repodata_version": 2,
        }
        shardlike = ShardLike(repodata, "https://example.com/linux-64/")
        # Should be able to retrieve python package
        assert "python" in shardlike
        shard = shardlike.visit_package("python")
        assert shard is not None
        assert "packages" in shard

    def test_add_pip_as_python_dependency_mentioned_packages(self):
        """Test that shard_mentioned_packages can include pip when requested"""
        shard = {
            "packages": {
                "python-3.10.0-h1234567_0.tar.bz2": {
                    "name": "python",
                    "depends": ["openssl", "readline"],
                }
            },
            "packages.conda": {},
        }
        # Test with extra=("pip",) to include pip
        packages = list(shard_mentioned_packages(shard, extra=("pip",)))
        assert "pip" in packages
        assert "openssl" in packages
        assert "readline" in packages

    def test_add_pip_as_python_dependency_filter_redundant(self):
        """Test package filtering with pip dependency consideration"""
        repodata = {
            "packages": {
                "python-3.10-0.tar.bz2": {"name": "python"},
                "pip-21.0-0.tar.bz2": {"name": "pip"},
            },
            "packages.conda": {
                "python-3.10-0.conda": {"name": "python"},
                "pip-21.0-0.conda": {"name": "pip"},
            },
        }
        # Should filter redundant tar.bz2 entries
        filtered = filter_redundant_packages(repodata, use_only_tar_bz2=False)
        # tar.bz2 versions should be removed
        assert "python-3.10-0.tar.bz2" not in filtered["packages"]
        # .conda versions should remain
        assert "python-3.10-0.conda" in filtered["packages.conda"]


def clean_cache(conda_cli: CondaCLIFixture):
    """
    Clean cache and assert it completed without error except on Windows
    """
    out, err, return_code = conda_cli("clean", "--yes", "--all")

    # Windows CI runners cannot reliably remove this file, so we don't care
    # about this assertion on that platform.

    # "err" will include log.debug output on certain test runners, so we can't
    # check it to determine whether there was an error.
    if not on_win:
        assert not return_code, "conda clean returned {return_code} != 0"


def repodata_subset_size(channel_data):
    """
    Measure the size of a repodata subset as serialized to JSON. Discard data.
    """
    repodata_size = 0
    for _, shardlike in channel_data.items():
        repodata = shardlike.build_repodata()
        repodata_text = json.dumps(
            repodata,
            indent=0,
            separators=(",", ":"),
            sort_keys=True,
            ensure_ascii=False,
        )
        repodata_size += len(repodata_text.encode("utf-8"))

    return repodata_size


@pytest.mark.integration
@pytest.mark.parametrize("cache_state", ("cold", "warm"))
@pytest.mark.parametrize("algorithm", ("bfs", "pipelined"))
@pytest.mark.parametrize(
    "scenario",
    TESTING_SCENARIOS,
    ids=[scenario["name"] for scenario in TESTING_SCENARIOS],
)
def test_traversal_algorithm_benchmarks(
    benchmark: BenchmarkFixture,
    cache_state: str,
    algorithm: str,
    scenario: dict,
):
    """
    Benchmark multiple traversal algorithms for retrieving repodata shards with
    a variety of parameter states (described below).

    cache_state:
        Either "cold" or "warm" representing shards available or not available in
        SQLite, respectively.

    algorithm:
        Method used to fetch shards

    scenario:
        List of packages to use to create an environment
    """
    cache = shards_cache.ShardCache(Path(conda.gateways.repodata.create_cache_dir()))
    if cache_state == "warm":
        # Clean shards cache just once for "warm"; leave index cache intact.
        cache.remove_cache()

    def setup():
        if cache_state != "warm":
            # For "cold", we want to clean shards cache before each round of benchmarking
            cache.remove_cache()

        channels = [Channel(f"{scenario['channel']}/{scenario['platform']}")]
        channel_data = fetch_channels(expand_channels(channels))

        assert channel_data is not None
        assert len(channel_data) in (2, 4), "Expected 2 or 4 channels fetched"

        subset = RepodataSubset((*channel_data.values(),))

        return (subset,), {}

    def target(subset: RepodataSubset):
        with _timer(""):
            subset.reachable(scenario["packages"], strategy=algorithm)

    warmup_rounds = 1 if cache_state == "warm" else 0

    benchmark.pedantic(target, setup=setup, rounds=1, warmup_rounds=warmup_rounds)


@pytest.mark.parametrize(
    "scenario",
    TESTING_SCENARIOS,
    ids=[scenario["name"] for scenario in TESTING_SCENARIOS],
)
def test_traversal_algorithms_match(conda_cli, scenario: dict):
    """
    Ensure that both BFS and pipelined algorithms return the same repodata subset.
    """
    channel = Channel(f"{scenario['channel']}/{scenario['platform']}")
    channels = expand_channels([channel])

    repodata_algorithm_map = {
        "bfs": build_repodata_subset(scenario["packages"], channels, algorithm="bfs"),
        "pipelined": build_repodata_subset(
            scenario["packages"], channels, algorithm="pipelined"
        ),
    }

    for subdir in repodata_algorithm_map["bfs"].keys():
        repodatas = []

        for _, repodata_subset in repodata_algorithm_map.items():
            assert repodata_subset
            repodatas.append(repodata_subset[subdir].build_repodata())

        assert all(x == y for x, y in zip(repodatas, repodatas[1:]))


# region pipelined


def test_shards_cache_thread(
    shard_cache_with_data: tuple[
        shards_cache.ShardCache, list[shards_cache.AnnotatedRawShard]
    ],
):
    """
    Test sqlite3 retrieval thread.
    """
    cache, fake_shards = shard_cache_with_data
    in_queue: SimpleQueue[list[NodeId] | None] = SimpleQueue()
    shard_out_queue: SimpleQueue[list[tuple[NodeId, ShardDict]]] = SimpleQueue()
    network_out_queue: SimpleQueue[list[NodeId]] = SimpleQueue()

    # this kind of thread can crash, and we don't hear back without our own
    # handling.
    cache_thread = threading.Thread(
        target=shards_subset.cache_fetch_thread,
        args=(in_queue, shard_out_queue, network_out_queue, cache),
        daemon=False,
    )

    fake_nodes = [
        NodeId(shard.package, channel="", shard_url=shard.url) for shard in fake_shards
    ]

    # several batches, then None "finish thread" sentinel
    in_queue.put(fake_nodes[:1])
    in_queue.put(
        [NodeId("notfound", channel="", shard_url="https://example.com/notfound")]
    )
    in_queue.put(fake_nodes[1:3])
    in_queue.put(
        [
            NodeId("notfound2", channel="", shard_url="https://example.com/notfound2"),
            NodeId("notfound3", channel="", shard_url="https://example.com/notfound3"),
        ]
    )
    in_queue.put(fake_nodes[3:])
    in_queue.put(None)

    cache_thread.start()

    # combined into a single output batch
    batch = shard_out_queue.get(timeout=QUEUE_TIMEOUT)
    for node_id, shard in batch:
        assert node_id in fake_nodes
        assert shard == cache.retrieve(node_id.shard_url)

    # no "done" sentinel in shard_out_queue
    with pytest.raises(queue.Empty):
        shard_out_queue.get_nowait()

    while notfound := network_out_queue.get(timeout=QUEUE_TIMEOUT):
        for node_id in notfound:
            assert node_id.shard_url.startswith("https://example.com/notfound")

    cache_thread.join(5)


def test_shards_network_thread(http_server_shards, shard_cache_with_data, monkeypatch):
    """
    Test network retrieval thread, meant to be chained after the sqlite3 thread
    by having network_in_queue = sqlite3 thread's network_out_queue.
    """
    # Timeout allows us to finish `with suppress(Empty)` loop more quickly, but
    # a too-short timeout can cause failures.
    monkeypatch.setattr(shards_subset, "QUEUE_TIMEOUT", 0.05)

    cache, fake_shards = shard_cache_with_data
    channel = Channel.from_url(f"{http_server_shards}/noarch")
    subdir_data = SubdirData(channel)
    found = fetch_shards_index(subdir_data)
    assert found

    invalid_shardlike = ShardLike(
        {},  # type: ignore
        url="file:///non-network/shard/url",
    )

    network_in_queue: SimpleQueue[list[NodeId] | None] = SimpleQueue()
    shard_out_queue: SimpleQueue[list[tuple[NodeId, ShardDict]]] = SimpleQueue()

    network_thread = threading.Thread(
        target=shards_subset.network_fetch_thread,
        args=(network_in_queue, shard_out_queue, cache, [found, invalid_shardlike]),
        daemon=False,
    )

    node_ids = [NodeId(package, found.url) for package in found.package_names]

    # Only fetch "foo" and "bar" because these are valid shards
    for node_id in node_ids:
        if node_id.package in ("foo", "bar"):
            network_in_queue.put([node_id])

    network_thread.start()

    urls = {}

    with suppress(Empty):
        while batch := shard_out_queue.get(timeout=shards_subset.QUEUE_TIMEOUT):
            for url, shard in batch:
                assert isinstance(shard, dict)

                # Make sure this is either one of the two packages from above ("foo" or "bar")
                assert set(shard.get("packages", {}).keys()).intersection(
                    (
                        "foo.tar.bz2",
                        "bar.tar.bz2",
                    )
                )

                urls[url] = shard

    assert len(urls) == 2

    # Expect TypeError if non-network NodeId is sent and one of the shardlikes
    # has its url. The worker thread will find that "nope" belongs to
    # invalid_shardlike: ShardLike (not Shards() type) and produce TypeError.
    network_in_queue.put([NodeId("nope", invalid_shardlike.url)])
    assert isinstance(shard_out_queue.get(timeout=1), TypeError)

    # Thread exits after exception.
    assert not network_thread.is_alive()

    # The network_in_queue() has an unnecessary None from its exception handler,
    # telling network_fetch_thread to quit but it already quit due to the
    # exception.
    assert network_in_queue.get() is None

    # New thread to test KeyError (invalid_shardlikes not in input args)
    network_thread = threading.Thread(
        target=shards_subset.network_fetch_thread,
        args=(network_in_queue, shard_out_queue, cache, [found]),
        daemon=False,
    )

    network_thread.start()

    network_in_queue.put([NodeId("nope", invalid_shardlike.url)])
    assert isinstance(shard_out_queue.get(timeout=1), KeyError)

    # Terminate with sentinel
    network_in_queue.put(None)

    network_thread.join(1)
    assert not network_thread.is_alive()


# endregion


@pytest.mark.parametrize("algorithm", ["bfs", "pipelined"])
def test_build_repodata_subset_error_propagation(
    http_server_shards, algorithm, mocker, tmp_path
):
    """
    Ensure errors encountered during shard fetching are properly propagated.

    This test uses http_server_shards to fetch the initial shards index,
    then mocks the actual shard fetching to simulate network errors.
    """

    # Use http_server_shards to set up the initial channel with shards index
    channel = Channel.from_url(f"{http_server_shards}/noarch")
    root_packages = ["foo"]

    # Override cache dir location for tests; ensures it's empty
    mocker.patch("conda.gateways.repodata.create_cache_dir", return_value=str(tmp_path))

    # Mock batch_retrieve_from_network to raise an error for bfs algorithm
    if algorithm == "bfs":
        with patch(
            "conda._private.shards.subset.batch_retrieve_from_network"
        ) as mock_batch:
            # Simulate a network error when fetching shards
            mock_batch.side_effect = HTTPError("Simulated network error")

            with pytest.raises(HTTPError, match="Simulated network error"):
                build_repodata_subset(
                    root_packages, expand_channels([channel]), algorithm=algorithm
                )

    # For pipelined algorithm, mock the session.get to raise an error
    elif algorithm == "pipelined":
        # Patch at the module level before threads start
        original_executor = shards_subset.ThreadPoolExecutor

        def mock_executor(*args, **kwargs):
            executor = original_executor(*args, **kwargs)
            original_submit = executor.submit

            def mock_submit(fn, *fn_args, **fn_kwargs):
                if fn.__name__ == "fetch":
                    raise HTTPError("Simulated network error during pipelined fetch")
                return original_submit(fn, *fn_args, **fn_kwargs)

            executor.submit = mock_submit
            return executor

        with patch("conda._private.shards.subset.ThreadPoolExecutor", mock_executor):
            # The pipelined algorithm should propagate this error
            with pytest.raises(
                HTTPError, match="Simulated network error during pipelined fetch"
            ):
                build_repodata_subset(
                    root_packages, expand_channels([channel]), algorithm=algorithm
                )


@pytest.mark.parametrize("algorithm", ["bfs", "pipelined"])
def test_build_repodata_subset_package_not_found(
    http_server_shards, algorithm, tmp_path, mocker
):
    """
    Ensure packages that cannot be found result in empty repodata.

    This test uses http_server_shards to fetch the initial shards index,
    and then tests the code to make sure an empty repodata is produced at the end.
    """

    # Use http_server_shards to set up the initial channel with shards index
    channel = Channel.from_url(f"{http_server_shards}/noarch")
    root_packages = ["404-package-not-found"]

    # Override cache dir location for tests; ensures it's empty
    mocker.patch("conda.gateways.repodata.create_cache_dir", return_value=str(tmp_path))

    channel_data = build_repodata_subset(
        root_packages, expand_channels([channel]), algorithm=algorithm
    )

    for shardlike in channel_data.values():
        assert not shardlike.build_repodata().get("packages")


@pytest.mark.parametrize("only_tar_bz2", (True, False))
@pytest.mark.parametrize("strategy", ("pipelined", "bfs"))
def test_only_tar_bz2(http_server_shards, tmp_path, only_tar_bz2, strategy):
    """
    Ensure we avoid tar_bz2 in "use .conda" mode.

    Should we exclude all .conda in "only .tar.bz2" mode? Can we drop this legacy mode?
    """
    channel = Channel.from_url(f"{http_server_shards}/noarch")
    root_packages = ["foo"]

    channel_data = fetch_channels({channel.url() or "": channel})
    subset = RepodataSubset((*channel_data.values(),))
    subset._use_only_tar_bz2 = only_tar_bz2
    subset.reachable(root_packages, strategy=strategy)

    repodata = json.dumps(subset.shardlikes[0].build_repodata(), indent=True)

    if only_tar_bz2:
        assert len(subset.shardlikes[0].build_repodata()["packages"]) > 0, repodata
    else:
        assert set(subset.shardlikes[0].build_repodata()["packages"]) == {
            "no-matching-conda.tar.bz2"
        }, repodata


def test_pipelined_with_slow_queue_operations(http_server_shards, mocker, tmp_path):
    """
    Test that simulates slow queue operations which can trigger race conditions
    where the main thread might timeout waiting for results.
    """
    channel = Channel.from_url(f"{http_server_shards}/noarch")
    root_packages = ["foo"]

    # Override cache dir location for tests
    mocker.patch("conda.gateways.repodata.create_cache_dir", return_value=str(tmp_path))

    # Create a custom queue that adds delays
    class SlowQueue(SimpleQueue):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.put_count = 0

        def put(self, item, *args, **kwargs):
            self.put_count += 1
            # Add delay every few puts to simulate slow operations
            if self.put_count % 3 == 0:
                time.sleep(0.05)
            return super().put(item, *args, **kwargs)

    def slow_simple_queue_factory(*args, **kwargs):
        # Only slow down shard_out_queue (not all queues)
        return SlowQueue(*args, **kwargs)

    mocker.patch("conda._private.shards.subset.SimpleQueue", slow_simple_queue_factory)

    # This should complete despite slow queue operations
    channel_data = build_repodata_subset(
        root_packages, expand_channels([channel]), algorithm="pipelined"
    )

    # Verify results
    found_packages = False
    for shardlike in channel_data.values():
        if "/noarch/" in shardlike.url and shardlike.build_repodata().get("packages"):
            found_packages = True
    assert found_packages


@pytest.mark.integration
def test_pipelined_shutdown_race_condition(http_server_shards, mocker, tmp_path):
    """
    Test the specific race condition where the main thread checks pending/in_flight
    and finds them empty, but worker threads are still processing items.
    """
    channel = Channel.from_url(f"{http_server_shards}/noarch")
    root_packages = ["foo"]

    mocker.patch("conda.gateways.repodata.create_cache_dir", return_value=str(tmp_path))

    # Track when drain_pending is called
    original_drain_pending = RepodataSubset._drain_pending
    drain_count = {"count": 0}

    def tracked_drain_pending(self, pending, shardlikes_by_url):
        drain_count["count"] += 1
        result = original_drain_pending(self, pending, shardlikes_by_url)
        # Add delay after drain to increase chance of race condition
        if drain_count["count"] > 1:
            time.sleep(0.1)
        return result

    mocker.patch.object(RepodataSubset, "_drain_pending", tracked_drain_pending)

    # Run multiple times to increase chance of hitting race condition
    for _ in range(10):
        channel_data = build_repodata_subset(
            root_packages, expand_channels([channel]), algorithm="pipelined"
        )

        # Verify we got valid results
        found_packages = False
        for shardlike in channel_data.values():
            if "/noarch/" in shardlike.url and shardlike.build_repodata().get(
                "packages"
            ):
                found_packages = True
        assert found_packages


@exception_to_queue
def cause_timeout_worker(
    in_queue,
    out_queue,
    _a,
    _b,
):
    """
    Grab items from in_queue without processing, causing timeouts.
    """
    for batch in combine_batches_until_none(in_queue):
        pass


@exception_to_queue
def dead_worker(
    in_queue,
    out_queue,
    _a,
    _b,
):
    """
    Exit without doing work.
    """


@pytest.mark.integration
def test_pipelined_timeout(http_server_shards, monkeypatch, tmp_path):
    """
    Test that pipelined times out if a URL is never fetched.
    """
    # Guarantee clean cache to avoid interference from previous tests
    monkeypatch.setenv("CONDA_PKGS_DIRS", str(tmp_path))
    monkeypatch.setenv("CONDA_REMOTE_READ_TIMEOUT_SECS", "1")
    monkeypatch.setenv("CONDA_REMOTE_MAX_RETRIES", "0")
    reset_context()

    channel = Channel.from_url(f"{http_server_shards}/noarch/")
    root_packages = ["foo"]

    # fetch_channels() will expand noarch/ to include context.subdirs, but we only want a single subdir here.
    # shardlikes = fetch_channels([channel])

    channel = Channel.from_url(f"{http_server_shards}/noarch")
    subdir_data = SubdirData(channel)
    shardlikes = [fetch_shards_index(subdir_data)]

    # faster failure. Now that we adjust timeouts based on
    # remote_read_timeout_secs, this doesn't do much.
    monkeypatch.setattr(
        "conda._private.shards.subset.REACHABLE_PIPELINED_MAX_TIMEOUTS", 1
    )
    # But, setting a shorter queue timeout period causes more timeouts to fire; exercising the "reach end of log_timeout()" path.
    monkeypatch.setattr("conda._private.shards.subset.QUEUE_TIMEOUT", 0.5)
    monkeypatch.setattr("conda._private.shards.subset.THREAD_WAIT_TIMEOUT", 0)

    assert len(shardlikes) == 1, "test expects a single channel"
    assert all(isinstance(shardlike, Shards) for shardlike in shardlikes), (
        "test expects real sharded channel"
    )
    subset = RepodataSubset(shardlikes)
    with (
        shards_cache.ShardCache(tmp_path) as cache,
        pytest.raises(TimeoutError, match="Timeout while fetching"),
    ):
        subset._reachable_pipelined(
            root_packages, network_worker=cause_timeout_worker, cache=cache
        )

    with (
        shards_cache.ShardCache(tmp_path) as cache,
        pytest.raises(TimeoutError, match="Timeout while fetching"),
    ):
        subset._reachable_pipelined(
            root_packages, network_worker=dead_worker, cache=cache
        )


def test_pipelined_uses_offline_worker(monkeypatch):
    """Test that expected worker is used in offline mode."""
    monkeypatch.setattr(context, "offline", True)

    actual_network_worker = None

    class RepodataSubsetRememberWorker(RepodataSubset):
        def _reachable_pipelined(self, root_packages, network_worker, cache):
            nonlocal actual_network_worker

            actual_network_worker = network_worker

    subset = RepodataSubsetRememberWorker([])
    subset.reachable_pipelined(["conda"])
    assert actual_network_worker is shards_subset.offline_nofetch_thread


@pytest.mark.integration
def test_combine_batches_blocking_scenario():
    """
    Test the scenario where combine_batches_until_none would block indefinitely
    without the timeout fix.

    This simulates the case where:
    1. Producer sends a few items
    2. Producer crashes or stops sending before sending None
    3. Consumer blocks forever waiting for more items
    """
    test_queue: SimpleQueue[Sequence[NodeId] | None] = SimpleQueue()

    # Put some items in the queue
    test_queue.put([NodeId("package1", "channel1")])
    test_queue.put([NodeId("package2", "channel2")])

    # Simulate producer failure - don't send None sentinel
    # Without timeout fix, this would block forever

    received = []
    timeout_occurred = False

    def consumer():
        nonlocal timeout_occurred
        try:
            for batch in combine_batches_until_none(test_queue):
                received.extend(batch)
                # After processing existing items, iterator should timeout
                # rather than block forever
        except Exception:
            timeout_occurred = True

    consumer_thread = threading.Thread(target=consumer, daemon=True)
    consumer_thread.start()

    # Wait for consumer to process existing items
    consumer_thread.join(timeout=2)

    # With the timeout fix, the thread should still be alive (waiting)
    # but not blocking indefinitely - it will timeout periodically
    # Let's verify it processed the items we sent
    assert len(received) == 2
    assert any(node.package == "package1" for node in received)


@pytest.mark.integration
def test_pipelined_extreme_race_conditions(
    prepare_shards_test,
    http_server_shards,
    mocker,
    tmp_path,
):
    """
    Introduce random delays in Queue operations to look for race conditions.

    This test:
    - Adds random delays at multiple points
    - Runs many iterations
    - Uses smaller timeouts
    - Simulates thread scheduling variability
    """
    channel = Channel("conda-forge-sharded/linux-64")
    root_packages = ["python", "vaex"]

    mocker.patch("conda.gateways.repodata.create_cache_dir", return_value=str(tmp_path))

    # Create a chaotic queue class that adds random delays
    class ChaoticQueue(SimpleQueue):
        def get(self, block=True, timeout=None):
            # Random delay before get
            if random.random() < 0.3:  # 30% chance
                time.sleep(random.uniform(0.001, 0.02))
            return super().get(block=block, timeout=timeout)

        def put(self, item, block=True, timeout=None):
            # Random delay before put
            if random.random() < 0.3:  # 30% chance
                time.sleep(random.uniform(0.001, 0.02))
            return super().put(item, block=block, timeout=timeout)

    # Patch at module level
    mocker.patch("conda._private.shards.subset.SimpleQueue", ChaoticQueue)

    # Run multiple iterations to increase chance of hitting race condition
    failures = []
    for iteration in range(20):
        try:
            channel_data = build_repodata_subset(
                root_packages, expand_channels([channel]), algorithm="pipelined"
            )

            # Verify we got results
            found = any(
                "/noarch/" in s.url and s.build_repodata().get("packages")
                for s in channel_data.values()
            )
            assert found, f"Iteration {iteration}: No packages found"
        except Exception as e:
            failures.append((iteration, str(e)))

    # With our fixes, there should be no failures
    assert not failures, f"Failed on iterations: {failures}"


@pytest.mark.parametrize("num_threads", [1, 2, 5])
def test_pipelined_concurrent_stress(http_server_shards, mocker, tmp_path, num_threads):
    """
    Run pipelined algorithm from multiple threads concurrently. This can expose
    race conditions in shared state or thread coordination.

    (Actually the concurrency issues happen in fetch_channels() which deals with
    reading, writing repodata_shards.msgpack.zst to disk.)
    """
    channel = Channel.from_url(f"{http_server_shards}/noarch")
    root_packages = ["foo"]

    mocker.patch("conda.gateways.repodata.create_cache_dir", return_value=str(tmp_path))

    errors = []

    def run_subset():
        try:
            channel_data = build_repodata_subset(
                root_packages, expand_channels([channel]), algorithm="pipelined"
            )
            # Verify results
            for shardlike in channel_data.values():
                if "/noarch/" in shardlike.url:
                    packages = shardlike.build_repodata().get("packages", {})
                    if packages:
                        return True
            return False
        except Exception as e:
            errors.append(e)
            raise

    # Run multiple instances concurrently
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(run_subset) for _ in range(num_threads)]
        results = [f.result(timeout=30) for f in futures]

    assert not errors, f"Errors occurred: {errors}"
    assert all(results), "Some runs didn't find packages"


def test_worker_thread_exception_propagation():
    """
    Test that exceptions in worker threads are properly propagated to main thread.
    Without proper exception handling, the main thread could timeout waiting for
    results that will never arrive.
    """
    in_queue = SimpleQueue()
    out_queue = SimpleQueue()

    @exception_to_queue
    def failing_worker(in_q, out_q):
        # Process one item successfully
        item = in_q.get()
        out_q.put(f"processed: {item}")

        # Then raise an exception
        raise ValueError("Simulated worker failure")

    # Put test data
    in_queue.put("test_item")

    # Run worker in thread
    worker = threading.Thread(
        target=failing_worker, args=(in_queue, out_queue), daemon=True
    )
    worker.start()

    # Should get the successful result first
    result = out_queue.get(timeout=QUEUE_TIMEOUT)
    assert result == "processed: test_item"

    # Should get the exception propagated
    exception = out_queue.get(timeout=QUEUE_TIMEOUT)
    assert isinstance(exception, ValueError)
    assert "Simulated worker failure" in str(exception)

    # Worker should also send None to in_queue to signal termination
    sentinel = in_queue.get(timeout=QUEUE_TIMEOUT)
    assert sentinel is None


def test_shutdown_with_pending_work(http_server_shards, mocker, tmp_path):
    """
    Test the race condition where main thread initiates shutdown while
    worker threads still have work in their queues.
    """
    channel = Channel.from_url(f"{http_server_shards}/noarch")
    root_packages = ["foo"]

    mocker.patch("conda.gateways.repodata.create_cache_dir", return_value=str(tmp_path))

    # Track shutdown events
    shutdown_events = []

    class TrackShutdownQueue(SimpleQueue):
        def put(self, item, *args, **kwargs):
            if item is None:
                shutdown_events.append(
                    {
                        "time": time.time(),
                        "thread": threading.current_thread().name,
                    }
                )
            return super().put(item, *args, **kwargs)

    # Patch at module level
    mocker.patch("conda._private.shards.subset.SimpleQueue", TrackShutdownQueue)

    # Run the algorithm
    channel_data = build_repodata_subset(
        root_packages, expand_channels([channel]), algorithm="pipelined"
    )

    # Verify we got results
    found = any(
        "/noarch/" in s.url and s.build_repodata().get("packages")
        for s in channel_data.values()
    )
    assert found

    # Verify shutdown was initiated (None was sent to queues)
    assert len(shutdown_events) > 0, "Shutdown was never initiated"


def test_repodata_subset_misc():
    """
    Test utility functions on RepodataSubset.
    """
    assert tuple(
        RepodataSubset.has_strategy(strategy)
        for strategy in ("bfs", "pipelined", "squirrel")
    ) == (True, True, False)
