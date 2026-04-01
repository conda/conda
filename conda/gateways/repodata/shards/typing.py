# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (C) 2022 Anaconda, Inc
# Copyright (C) 2023 conda
# SPDX-License-Identifier: BSD-3-Clause
"""
TypedDict declarations for sharded repodata.

Helpful for typing; do not validate at runtime.
"""

from __future__ import annotations

import sys
from typing import TypedDict

if sys.version_info >= (3, 11):
    from typing import NotRequired
else:
    from typing_extensions import NotRequired  # noqa: TC002


class PackageRecordDict(TypedDict):
    """
    Basic package attributes that this module cares about.
    """

    name: str
    version: str
    build: str
    build_number: int
    sha256: NotRequired[str | bytes]
    md5: NotRequired[str | bytes]
    depends: list[str]
    constrains: NotRequired[list[str]]
    noarch: NotRequired[str]


# in this style because "packages.conda" is not a Python identifier
ShardDict = TypedDict(
    "ShardDict",
    {
        "packages": dict[str, PackageRecordDict],
        "packages.conda": dict[str, PackageRecordDict],
    },
)


class RepodataInfoDict(TypedDict):
    base_url: str  # where packages are stored
    shards_base_url: str  # where shards are stored
    subdir: str


class RepodataDict(ShardDict):
    """
    Packages plus info.
    """

    info: RepodataInfoDict
    repodata_version: int


class ShardsIndexDict(TypedDict):
    """
    Shards index as deserialized from repodata_shards.msgpack.zst
    """

    info: RepodataInfoDict
    version: int  # TODO conda-index currently uses 'repodata_version' here
    shards: dict[str, bytes]
