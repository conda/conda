# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Bounded decompression for sharded repodata."""

from __future__ import annotations

from conda.common.url import mask_anaconda_token, remove_auth
from conda.exceptions import ChannelError

from ..zstd import ZstdError, capped_decompress

ZSTD_MAX_SHARD_SIZE = (
    2**20 * 64
)  # maximum decompressed size of an individual package shard

ZSTD_MAX_SHARD_WINDOW_SIZE = 2**20 * 16  # maximum zstd decoder window size

ZSTD_MAX_SHARD_INDEX_SIZE = (
    2**23 * 16
)  # maximum size necessary when compressed data has no size header


def decompress_shard(data: bytes, *, url: str, package: str) -> bytes:
    """Decompress an individual shard and translate errors for conda users."""
    try:
        return capped_decompress(
            data,
            max_output_size=ZSTD_MAX_SHARD_SIZE,
            max_window_size=ZSTD_MAX_SHARD_WINDOW_SIZE,
        )
    except ZstdError as err:
        safe_url = remove_auth(mask_anaconda_token(url))
        message = (
            f"repodata shard for package {package!r} from channel {safe_url!r}: "
            f"{err} (output limit: {ZSTD_MAX_SHARD_SIZE} bytes, "
            f"decoder window limit: {ZSTD_MAX_SHARD_WINDOW_SIZE} bytes)"
        )
        raise ChannelError(message, caused_by=err) from err
