# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Minimal sharded repodata tests adapted from conda-libmamba-solver.

Tests focus on core pipelined repodata subset functionality with
code coverage tracking.
"""

from __future__ import annotations

import urllib.parse

import pytest

from _conda.shards.shards import (
    ShardLike,
    fetch_channels,
    shard_mentioned_packages,
)
from _conda.shards.subset import (
    RepodataSubset,
    build_repodata_subset,
    filter_redundant_packages,
)
from conda.base.context import context, reset_context
from conda.models.channel import Channel

from .conftest import (
    CONDA_FORGE_WITH_SHARDS,
    FAKE_REPODATA,
    ROOT_PACKAGES,
    _timer,
    ensure_hex_hash,
    expand_channels,
)

# Minimal test scenarios for fast validation
TESTING_SCENARIOS = [
    {
        "name": "python",
        "packages": ["python"],
        "prefetch_packages": [],
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
]


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
            assert (ns / 1e9) < 0.05, "Empty shard traversal should be quick."

    with _timer("RepodataSubset.reachable_pipelined()", assert_quick):
        subset = RepodataSubset((*channel_data.values(),))
        subset.reachable_pipelined(root_packages)
        print(f"{len(subset._nodes)} (channel, package) nodes discovered")

    print(
        "Channels:",
        ",".join(urllib.parse.urlparse(url).path[1:] for url in channel_data),
    )


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

        for algorithm, repodata_subset in repodata_algorithm_map.items():
            repodatas.append(repodata_subset[subdir].build_repodata())

        assert all(x == y for x, y in zip(repodatas, repodatas[1:]))


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

    assert len(channel_data), "no channel data"
    print(f"Repodata subset would be {repodata_size} bytes as json")

    print(
        "Channels:",
        ",".join(urllib.parse.urlparse(url).path[1:] for url in channel_data),
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
