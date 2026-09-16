# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Resolve channel priority relations declared in repodata (CEP 42)."""

from __future__ import annotations

from collections import deque
from collections.abc import Mapping
from posixpath import normpath
from typing import TYPE_CHECKING
from urllib.parse import urlsplit, urlunsplit

from ..base.constants import REPODATA_FN
from ..base.context import context, validate_channels
from ..exceptions import ChannelError
from ..models.channel import Channel

if TYPE_CHECKING:
    from collections.abc import Iterable


def _related_channel(channel: Channel, reference: object) -> Channel:
    if not isinstance(reference, str) or not reference.startswith("../"):
        raise ChannelError(
            f"Channel relation for {channel.base_url} must be a relative path starting with '../'."
        )
    parts = urlsplit(reference)
    if (
        parts.scheme
        or parts.netloc
        or parts.query
        or parts.fragment
        or "\\" in reference
    ):
        raise ChannelError(f"Invalid channel relation for {channel.base_url}.")
    origin = urlsplit(channel.base_url)
    path = normpath(f"{origin.path.rstrip('/')}/{parts.path}")
    related = Channel(urlunsplit(origin._replace(path=path)))
    # A path token belongs to the declaring channel. Resolve the target's token
    # through normal channel configuration instead of forwarding that token.
    target = urlsplit(related.base_url)
    if (
        channel.auth
        and not related.auth
        and (origin.scheme, origin.netloc) == (target.scheme, target.netloc)
    ):
        related = Channel(**{**related.dump(), "auth": channel.auth})
    return related


def resolve_channel_relations(
    channels: Iterable[Channel | str],
    subdirs: Iterable[str] | None = None,
    *,
    repodata_fn: str = REPODATA_FN,
    max_depth: int | None = None,
    use_shards: bool | None = None,
) -> tuple[Channel, ...]:
    """Return channels in priority order after discovering their CEP 42 relations.

    Expand multichannels into individual channels and preserve explicit head
    ordering. Callers should keep the original heads when recording environment
    configuration or lockfiles. A maximum depth of zero disables discovery.

    All metadata is obtained through conda's normal repodata and shard fetchers.
    Related channels are checked against channel policy before metadata is read.
    Explicit ``subdirs`` override any platform in the input channels, matching
    :meth:`Channel.urls`. ``noarch`` is always included during discovery.
    """
    from .._private.shards.shards import fetch_shards_index
    from .subdir_data import SubdirData

    max_depth = context.channel_relations_max_depth if max_depth is None else max_depth
    if max_depth < 0:
        raise ChannelError("channel_relations_max_depth must be non-negative.")
    use_shards = context.repodata_use_shards if use_shards is None else use_shards
    heads = {}
    for value in channels:
        for channel in Channel(value).channels:
            if channel.base_url is not None:
                heads.setdefault(channel.base_url, channel)
    validate_channels(tuple(heads.values()))
    if not max_depth or not heads:
        return tuple(heads.values())

    if subdirs is None:
        subdirs = tuple(
            dict.fromkeys(
                subdir
                for channel in heads.values()
                for subdir in ((channel.subdir,) if channel.subdir else context.subdirs)
            )
        )
    subdirs = tuple(dict.fromkeys((*subdirs, "noarch")))
    nodes = dict(heads)
    head_order = {url: i for i, url in enumerate(heads)}
    successors = {url: [] for url in heads}
    for before, after in zip(heads, tuple(heads)[1:]):
        successors[before].append(after)

    pending = deque((url, 0) for url in heads)
    while pending:
        url, depth = pending.popleft()
        channel = nodes[url]
        for subdir in subdirs:
            source = SubdirData(
                Channel(**{**channel.dump(), "platform": subdir}),
                repodata_fn=repodata_fn,
            )
            if use_shards and (shards := fetch_shards_index(source)) is not None:
                relations = shards.repodata_no_packages.get("info", {}).get(
                    "channel_relations", {}
                )
            else:
                relations = source.channel_relations
            if not isinstance(relations, Mapping):
                raise ChannelError(f"Channel relations for {url} must be a mapping.")
            targets = {
                key: _related_channel(channel, relations[key])
                for key in ("base", "overrides")
                if key in relations
            }
            if (
                "base" in targets
                and "overrides" in targets
                and targets["base"].base_url == targets["overrides"].base_url
            ):
                raise ChannelError(
                    f"Channel {url} declares the same base and overrides."
                )
            for key, target in targets.items():
                target_url = target.base_url
                if target_url not in nodes:
                    if depth >= max_depth:
                        raise ChannelError(
                            f"Channel relation depth exceeds {max_depth} at {url}."
                        )
                    validate_channels((target,))
                    nodes[target_url] = target
                    successors[target_url] = []
                    pending.append((target_url, depth + 1))
                before, after = (
                    (target_url, url) if key == "base" else (url, target_url)
                )
                if (
                    before in head_order
                    and after in head_order
                    and head_order[before] > head_order[after]
                ):
                    continue
                if after not in successors[before]:
                    successors[before].append(after)

    resolved = []
    visited = set()
    active = set()
    # Visit heads in reverse priority order so unrelated heads do not separate
    # channels connected by relations when several topological orders are valid.
    for root in (*reversed(heads), *reversed(nodes)):
        if root in visited:
            continue
        active.add(root)
        pending_nodes = [(root, iter(successors[root]))]
        while pending_nodes:
            url, following = pending_nodes[-1]
            after = next(following, None)
            if after is None:
                pending_nodes.pop()
                active.remove(url)
                visited.add(url)
                resolved.append(nodes[url])
            elif after in active:
                raise ChannelError(
                    f"Channel relations contain a cycle involving {after}."
                )
            elif after not in visited:
                active.add(after)
                pending_nodes.append((after, iter(successors[after])))
    return tuple(reversed(resolved))
