# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (C) 2022 Anaconda, Inc
# Copyright (C) 2023 conda
# SPDX-License-Identifier: BSD-3-Clause
"""
Solver-agnostic sharded repodata: fetch, cache, traversal, and subset building.
"""

from __future__ import annotations

from .cache import AnnotatedRawShard, ShardCache
from .core import (
    ShardBase,
    ShardLike,
    Shards,
    batch_retrieve_from_cache,
    batch_retrieve_from_network,
    default_parse_dep_name,
    ensure_hex_hash,
    fetch_channels,
    fetch_shards_index,
    shard_mentioned_packages,
)
from .subset import (
    Node,
    NodeId,
    RepodataSubset,
    build_repodata_subset,
    filter_redundant_packages,
)
from .typing import (
    PackageRecordDict,
    RepodataDict,
    RepodataInfoDict,
    ShardDict,
    ShardsIndexDict,
)

__all__ = [
    "AnnotatedRawShard",
    "Node",
    "NodeId",
    "PackageRecordDict",
    "RepodataDict",
    "RepodataInfoDict",
    "RepodataSubset",
    "ShardBase",
    "ShardCache",
    "ShardDict",
    "ShardLike",
    "Shards",
    "ShardsIndexDict",
    "batch_retrieve_from_cache",
    "batch_retrieve_from_network",
    "build_repodata_subset",
    "default_parse_dep_name",
    "ensure_hex_hash",
    "fetch_channels",
    "fetch_shards_index",
    "filter_redundant_packages",
    "shard_mentioned_packages",
]
