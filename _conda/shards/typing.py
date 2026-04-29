# Copyright (C) 2022 Anaconda, Inc
# Copyright (C) 2023 conda
# SPDX-License-Identifier: BSD-3-Clause
"""
TypedDict declarations for shards.

These are helpful for auto-complete, but do not validate at runtime and are not
normative. They are intentionally not shared with another project (conda) to
reduce coupling.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from typing import NotRequired


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


class RepodataInfoDict(TypedDict):  # noqa: F811
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
