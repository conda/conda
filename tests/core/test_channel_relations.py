# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import msgpack
import pytest

from conda._private.zstd import compress
from conda.base.context import Context, context, reset_context
from conda.common.configuration import ValidationError
from conda.common.serialize import json
from conda.core import index as channel_index
from conda.core.index import Index
from conda.core.solve import Solver
from conda.core.subdir_data import SubdirData
from conda.exceptions import ChannelError, DryRunExit
from conda.models.channel import Channel, MultiChannel

if not hasattr(channel_index, "resolve_channels"):
    pytest.skip(
        "Channel resolution is unavailable in the benchmark comparison baseline",
        allow_module_level=True,
    )
resolve_channels = channel_index.resolve_channels


@pytest.fixture
def relations(mocker):
    metadata = {}
    read = mocker.Mock(
        side_effect=lambda source: metadata.get(
            (source.channel.name, source.channel.subdir), {}
        )
    )
    mocker.patch.object(SubdirData, "channel_relations", property(read))
    mocker.patch.object(context, "repodata_use_shards", False)
    mocker.patch.object(context, "channel_relations_max_depth", 10, create=True)
    mocker.patch.object(context, "allowlist_channels", ())
    mocker.patch.object(context, "denylist_channels", ())
    return metadata, read


def names(channels):
    return [channel.name for channel in channels]


def test_transitive_bases(relations):
    metadata, read = relations
    metadata["alpha", "linux-64"] = {"base": "../beta", "future": "ignored"}
    metadata["beta", "noarch"] = {"base": "../gamma"}
    assert names(resolve_channels(["https://example.org/alpha"], ["linux-64"])) == [
        "gamma",
        "beta",
        "alpha",
    ]
    assert read.call_count == 6


def test_base_and_overrides(relations):
    metadata, _ = relations
    metadata["alpha", "noarch"] = {"base": "../beta", "overrides": "../gamma"}
    assert names(resolve_channels(["https://example.org/alpha"], ["noarch"])) == [
        "beta",
        "alpha",
        "gamma",
    ]


@pytest.mark.parametrize("heads", [("alpha", "beta"), ("beta", "alpha")])
def test_explicit_order(relations, heads):
    metadata, _ = relations
    metadata["alpha", "noarch"] = {"base": "../beta"}
    assert names(
        resolve_channels([f"https://example.org/{name}" for name in heads], ["noarch"])
    ) == list(heads)


def test_nonadjacent_explicit_order(relations):
    metadata, _ = relations
    metadata["alpha", "noarch"] = {"base": "../gamma"}
    assert names(
        resolve_channels(
            [f"https://example.org/{name}" for name in ("alpha", "beta", "gamma")],
            ["noarch"],
        )
    ) == ["alpha", "beta", "gamma"]


@pytest.mark.parametrize(
    "relations_by_name",
    [
        {"alpha": {"base": "../beta"}, "beta": {"base": "../alpha"}},
        {"alpha": {"base": "../gamma"}, "gamma": {"base": "../beta"}},
        {"alpha": {"base": "../alpha"}},
    ],
)
def test_cycles(relations, relations_by_name):
    metadata, _ = relations
    metadata.update(
        {(name, "noarch"): value for name, value in relations_by_name.items()}
    )
    heads = ["https://example.org/alpha"]
    if "gamma" in relations_by_name:
        heads.append("https://example.org/beta")
    with pytest.raises(ChannelError, match="cycle"):
        resolve_channels(heads, ["noarch"])


def test_same_base_and_overrides(relations):
    metadata, _ = relations
    metadata["alpha", "noarch"] = {"base": "../beta", "overrides": "../nested/../beta"}
    with pytest.raises(ChannelError, match="same base and overrides"):
        resolve_channels(["https://example.org/alpha"], ["noarch"])


def test_union_subdirs_and_deduplicate(relations):
    metadata, read = relations
    metadata["alpha", "linux-64"] = {"base": "../beta"}
    metadata["alpha", "noarch"] = {"overrides": "../gamma"}
    metadata["gamma", "noarch"] = {"base": "../beta"}
    assert names(resolve_channels(["https://example.org/alpha"], ["linux-64"])) == [
        "beta",
        "alpha",
        "gamma",
    ]
    assert read.call_count == 6


def test_only_requested_subdirs(relations):
    metadata, read = relations
    metadata["alpha", "win-64"] = {"base": "../unused"}
    assert names(resolve_channels(["https://example.org/alpha"], ["linux-64"])) == [
        "alpha"
    ]
    assert {call.args[0].channel.subdir for call in read.call_args_list} == {
        "linux-64",
        "noarch",
    }


def test_explicit_platform_without_subdirs(relations):
    _, read = relations
    resolve_channels(["https://example.org/alpha/win-64"])
    assert {call.args[0].channel.subdir for call in read.call_args_list} == {
        "win-64",
        "noarch",
    }


def test_multichannels(relations):
    heads = MultiChannel(
        "example",
        (Channel("https://example.org/alpha"), Channel("https://example.org/beta")),
    )
    assert names(resolve_channels([heads], ["noarch"])) == ["alpha", "beta"]


def test_depth_limit(relations):
    metadata, read = relations
    metadata["alpha", "noarch"] = {"base": "../beta"}
    metadata["beta", "noarch"] = {"base": "../gamma"}
    with pytest.raises(ChannelError, match="depth exceeds 1"):
        resolve_channels(["https://example.org/alpha"], ["noarch"], max_depth=1)
    assert read.call_count == 2


def test_disabled_does_not_fetch(relations):
    _, read = relations
    assert names(resolve_channels(["https://example.org/alpha"], max_depth=0)) == [
        "alpha"
    ]
    read.assert_not_called()


@pytest.mark.parametrize("value", [-1, -10])
def test_negative_depth(relations, value):
    with pytest.raises(ChannelError, match="non-negative"):
        resolve_channels([], max_depth=value)


@pytest.mark.parametrize(
    "reference",
    [
        "alpha",
        "./alpha",
        "https://example.org/alpha",
        "//example.org/alpha",
        "../alpha?query",
        "../alpha#fragment",
        "../alpha\\beta",
        None,
        [],
        1,
    ],
)
def test_invalid_reference(relations, reference):
    metadata, _ = relations
    metadata["alpha", "noarch"] = {"base": reference}
    with pytest.raises(ChannelError):
        resolve_channels(["https://example.org/alpha"], ["noarch"])


@pytest.mark.parametrize("value", [None, [], "../alpha"])
def test_invalid_relations_object(relations, value):
    metadata, _ = relations
    metadata["alpha", "noarch"] = value
    with pytest.raises(ChannelError, match="must be a mapping"):
        resolve_channels(["https://example.org/alpha"], ["noarch"])


@pytest.mark.parametrize(
    "url, reference, expected",
    [
        ("https://example.org/alpha/label/rc", "../..", "https://example.org/alpha"),
        ("https://example.org/alpha", "../beta", "https://example.org/beta"),
        ("file:///tmp/channels/alpha", "../beta", "file:///tmp/channels/beta"),
        ("s3://example.org/alpha", "../beta", "s3://example.org/beta"),
    ],
)
def test_relative_paths(relations, url, reference, expected):
    metadata, _ = relations
    metadata[Channel(url).name, "noarch"] = {"base": reference}
    result = resolve_channels([url], ["noarch"])
    assert [channel.base_url for channel in result] == [expected, url]


def test_token_is_not_forwarded(relations):
    metadata, _ = relations
    metadata["alpha", "noarch"] = {"base": "../beta"}
    source = Channel("https://example.org/t/secret/alpha")
    target, _ = resolve_channels([source], ["noarch"])
    assert target.token is None
    assert target.base_url == "https://example.org/beta"


def test_basic_credentials(relations):
    metadata, _ = relations
    metadata["alpha", "noarch"] = {"base": "../beta"}
    source = Channel("https://user:password@example.org/alpha")
    target, _ = resolve_channels([source], ["noarch"])
    assert target.auth == "user:password"


def test_policy_applies_before_fetching_related_channel(relations, mocker):
    metadata, read = relations
    metadata["alpha", "noarch"] = {"base": "../beta"}
    mocker.patch.object(context, "denylist_channels", ("https://example.org/beta",))
    with pytest.raises(ChannelError):
        resolve_channels(["https://example.org/alpha"], ["noarch"])
    assert read.call_count == 1


def test_local_repodata_discovery_and_query(tmp_path, mocker):
    mocker.patch.object(context, "channel_relations_max_depth", 10, create=True)
    mocker.patch.object(context, "allowlist_channels", ())
    mocker.patch.object(context, "denylist_channels", ())
    for name, info in {
        "alpha": {"channel_relations": {"base": "../beta"}},
        "beta": {},
    }.items():
        subdir = tmp_path / name / "noarch"
        subdir.mkdir(parents=True)
        packages = (
            {
                "example-1.0-0.tar.bz2": {
                    "name": "example",
                    "version": "1.0",
                    "build": "0",
                    "build_number": 0,
                    "depends": [],
                    "subdir": "noarch",
                }
            }
            if name == "beta"
            else {}
        )
        (subdir / "repodata.json").write_text(
            json.dumps({"info": {"subdir": "noarch", **info}, "packages": packages})
        )
    head = (tmp_path / "alpha").as_uri()
    result = resolve_channels([head], ["noarch"], use_shards=False)
    assert [channel.base_url for channel in result] == [
        (tmp_path / "beta").as_uri(),
        head,
    ]
    index = Index(channels=[head], subdirs=("noarch",), prepend=False)
    assert index._channels == (head,)
    assert len(index) == 1
    assert [channel.base_url for channel in index.expanded_channels] == [
        (tmp_path / "beta").as_uri(),
        head,
    ]
    records = SubdirData.query_all("example", [head], ["noarch"])
    assert len(records) == 1
    assert records[0].channel.base_url == (tmp_path / "beta").as_uri()


def test_related_channels_stay_adjacent(relations):
    metadata, _ = relations
    metadata["alpha", "noarch"] = {"overrides": "../gamma"}
    assert names(
        resolve_channels(
            ["https://example.org/alpha", "https://example.org/beta"], ["noarch"]
        )
    ) == ["alpha", "gamma", "beta"]


def test_many_explicit_heads_do_not_exceed_python_recursion_limit(relations):
    heads = [f"https://example.org/channel-{i}" for i in range(1100)]
    assert [
        channel.base_url for channel in resolve_channels(heads, ["noarch"])
    ] == heads


def test_index_defers_discovery(relations):
    _, read = relations
    index = Index(
        channels=["https://example.org/alpha"], subdirs=("noarch",), prepend=False
    )
    read.assert_not_called()
    assert index._channels == ("https://example.org/alpha",)


@pytest.mark.usefixtures("solver_classic")
@pytest.mark.parametrize("relation, expected", [("base", "1.0"), ("overrides", "2.0")])
def test_classic_dry_run_uses_related_channel_priority(
    tmp_path, monkeypatch, conda_cli, relation, expected
):
    monkeypatch.setenv("CONDA_PKGS_DIRS", str(tmp_path / "pkgs"))
    monkeypatch.setenv("CONDA_ENVS_PATH", str(tmp_path / "envs"))
    monkeypatch.setenv("CONDA_CHANNEL_RELATIONS_MAX_DEPTH", "10")
    for name, version in (("alpha", "2.0"), ("beta", "1.0")):
        subdir = tmp_path / name / "noarch"
        subdir.mkdir(parents=True)
        info = {"subdir": "noarch"}
        if name == "alpha":
            info["channel_relations"] = {relation: "../beta"}
        package = {
            "name": "example",
            "version": version,
            "build": "0",
            "build_number": 0,
            "depends": [],
            "subdir": "noarch",
            "size": 1,
            "md5": "0" * 32,
            "sha256": "0" * 64,
        }
        (subdir / "repodata.json").write_text(
            json.dumps(
                {"info": info, "packages": {f"example-{version}-0.tar.bz2": package}}
            )
        )
    stdout, _, _ = conda_cli(
        "create",
        "--prefix",
        str(tmp_path / "environment"),
        "--dry-run",
        "--json",
        "--solver",
        "classic",
        "--strict-channel-priority",
        "--override-channels",
        "--channel",
        (tmp_path / "alpha").as_uri(),
        "--no-default-packages",
        "example",
        raises=DryRunExit,
    )
    result = json.loads(stdout)
    assert result["success"]
    assert [
        (record["name"], record["version"]) for record in result["actions"]["LINK"]
    ] == [("example", expected)]


def test_max_depth_configuration_rejects_negative(tmp_path):
    path = tmp_path / ".condarc"
    path.write_text("channel_relations_max_depth: -1\n")
    configured = Context(search_path=(path,))
    with pytest.raises(ValidationError, match="non-negative"):
        configured.channel_relations_max_depth


def test_local_shard_relations(tmp_path):
    for name, relations in (("alpha", {"base": "../beta"}), ("beta", {})):
        subdir = tmp_path / name / "noarch"
        subdir.mkdir(parents=True)
        index = {
            "info": {
                "subdir": "noarch",
                "base_url": "",
                "shards_base_url": "",
                "channel_relations": relations,
            },
            "shards": {},
        }
        (subdir / "repodata_shards.msgpack.zst").write_bytes(
            compress(msgpack.dumps(index))
        )
    head = (tmp_path / "alpha").as_uri()
    resolved = resolve_channels([head], ["noarch"], use_shards=True)
    assert [channel.base_url for channel in resolved] == [
        (tmp_path / "beta").as_uri(),
        head,
    ]


@pytest.mark.usefixtures("solver_classic")
@pytest.mark.parametrize("realized", (False, True))
def test_provided_index_relations_set_solver_priority(tmp_path, monkeypatch, realized):
    monkeypatch.setenv("CONDA_CHANNEL_PRIORITY", "strict")
    reset_context()
    for name, version in (("alpha", "2.0"), ("beta", "1.0")):
        subdir = tmp_path / name / "noarch"
        subdir.mkdir(parents=True)
        info = {"subdir": "noarch"}
        if name == "alpha":
            info["channel_relations"] = {"base": "../beta"}
        package = {
            "name": "example",
            "version": version,
            "build": "0",
            "build_number": 0,
            "depends": [],
            "subdir": "noarch",
        }
        (subdir / "repodata.json").write_text(
            json.dumps(
                {"info": info, "packages": {f"example-{version}-0.tar.bz2": package}}
            )
        )
    heads = ((tmp_path / "alpha").as_uri(),)
    index = Index(
        channels=heads,
        subdirs=("noarch",),
        prepend=False,
        prefix=tmp_path / "other",
        use_system=True,
    )
    if realized:
        index.data
    solver = Solver(
        prefix=tmp_path / "target",
        channels=heads,
        subdirs=("noarch",),
        specs_to_add=("example",),
    )
    solver._index = index
    result = solver.solve_final_state()
    assert [(record.name, record.version) for record in result] == [("example", "1.0")]
    assert index._channels == heads
    assert tuple(channel.base_url for channel in solver.channels) == heads


def test_unchanged_multichannel_keeps_index_mapping(relations):
    head = MultiChannel(
        "example",
        (Channel("https://example.org/alpha"), Channel("https://example.org/beta")),
    )
    index = Index(channels=[head], subdirs=("noarch",), prepend=False)
    before = index.channels.copy()
    index.resolve_channels()
    assert index.channels == before
    assert tuple(index.channels) == (head,)
