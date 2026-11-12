# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from types import SimpleNamespace

import msgpack
import pytest

from conda._private.shards import shards
from conda._private.zstd import compress
from conda.base.context import context
from conda.common.serialize import json
from conda.core import index as channel_index
from conda.core.subdir_data import SubdirData
from conda.exceptions import ChannelError
from conda.plugins import hookimpl, types

if not hasattr(types, "CondaPreChannelFetch"):
    pytest.skip(
        "Channel fetch checks are unavailable in the baseline", allow_module_level=True
    )
resolve_channels = channel_index.resolve_channels


@pytest.fixture
def repositories(tmp_path):
    for name, relations in (("head", {"base": "../related"}), ("related", {})):
        subdir = tmp_path / name / "noarch"
        subdir.mkdir(parents=True)
        info = {"subdir": "noarch", "channel_relations": relations}
        (subdir / "repodata.json").write_text(
            json.dumps({"info": info, "packages": {}, "packages.conda": {}})
        )
        (subdir / "repodata_shards.msgpack.zst").write_bytes(
            compress(
                msgpack.dumps(
                    {
                        "info": {**info, "base_url": "", "shards_base_url": ""},
                        "shards": {},
                    }
                )
            )
        )
    return (tmp_path / "head").as_uri(), (tmp_path / "related").as_uri()


@pytest.mark.parametrize("use_shards", (False, True))
@pytest.mark.parametrize("reject_in_callback", (False, True))
def test_rejection_prevents_related_metadata(
    repositories, plugin_manager, mocker, use_shards, reject_in_callback
):
    head, related = repositories
    events = []

    def callback(channel):
        events.append(("callback", channel.base_url))
        if channel.base_url == related and reject_in_callback:
            raise ChannelError("Repository access is required")

    def provider(channel):
        events.append(("provider", channel.base_url))
        if channel.base_url == related:
            raise ChannelError("Repository access is required")

    @hookimpl
    def conda_pre_channel_fetches():
        yield types.CondaPreChannelFetch("repository-policy", provider)

    plugin_manager.register(
        SimpleNamespace(conda_pre_channel_fetches=conda_pre_channel_fetches)
    )
    reads = (
        mocker.spy(shards, "fetch_shards_index")
        if use_shards
        else mocker.spy(SubdirData, "load")
    )
    with pytest.raises(ChannelError, match="access is required"):
        resolve_channels(
            [head], ["noarch"], before_fetch=callback, use_shards=use_shards
        )
    expected = [("callback", head), ("provider", head), ("callback", related)]
    if not reject_in_callback:
        expected.append(("provider", related))
    assert events == expected
    assert reads.call_args_list
    assert all(call.args[0].channel.base_url == head for call in reads.call_args_list)


@pytest.mark.parametrize("depth", (0, 10))
def test_checks_repeat_for_cached_channels(repositories, plugin_manager, depth):
    head, related = repositories
    checked = []

    @hookimpl
    def conda_pre_channel_fetches():
        yield types.CondaPreChannelFetch(
            "repository-policy", lambda channel: checked.append(channel.base_url)
        )

    plugin_manager.register(
        SimpleNamespace(conda_pre_channel_fetches=conda_pre_channel_fetches)
    )
    for _ in range(2):
        resolve_channels([head], ["noarch"], max_depth=depth, use_shards=False)
    assert checked == ([head, related] * 2 if depth else [head, head])


def test_channel_policy_precedes_provider_checks(repositories, plugin_manager, mocker):
    head, related = repositories
    checked = []

    @hookimpl
    def conda_pre_channel_fetches():
        yield types.CondaPreChannelFetch(
            "repository-policy", lambda channel: checked.append(channel.base_url)
        )

    plugin_manager.register(
        SimpleNamespace(conda_pre_channel_fetches=conda_pre_channel_fetches)
    )
    mocker.patch.object(context, "denylist_channels", (related,))
    with pytest.raises(ChannelError):
        resolve_channels([head], ["noarch"], use_shards=False)
    assert checked == [head]
