# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Bounded decompression for sharded repodata."""

from __future__ import annotations

from conda.common.url import mask_anaconda_token, remove_auth
from conda.exceptions import ChannelError

from ..zstd import ZstdError, capped_decompress

# Individual package shards can exceed the original 16 MiB limit as channel
# history grows.
ZSTD_MAX_SHARD_SIZE = 2**20 * 64

# Allow shard-index frames without a decompressed-size header up to 128 MiB.
ZSTD_MAX_SHARD_INDEX_SIZE = 2**23 * 16


def decompress_shard(data: bytes, *, url: str, package: str) -> bytes:
    """Decompress an individual shard and translate errors for conda users."""
    try:
        return capped_decompress(
            data,
            max_output_size=ZSTD_MAX_SHARD_SIZE,
        )
    except ZstdError as err:
        safe_url = remove_auth(mask_anaconda_token(url))
        message = (
            f"repodata shard for package {package!r} from channel {safe_url!r}: "
            f"{err} (output and decoder window limit: "
            f"{ZSTD_MAX_SHARD_SIZE} bytes)"
        )
        raise ChannelError(message, caused_by=err) from err
