# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""compression.zstd (stdlib or backports.zstd) bindings for conda."""

from __future__ import annotations

import math
import sys

if sys.version_info >= (3, 14):
    from compression import zstd
else:
    from backports import zstd

ZstdError = zstd.ZstdError  # single symbol for callers to catch

__all__ = ["ZstdError", "capped_decompress", "zstd"]


def capped_decompress(data: bytes, max_output_size: int) -> bytes:
    """One-shot decompress of untrusted data with output and window bounds.

    Replaces ``zstandard.decompress(..., max_output_size=...)`` and
    ``ZstdDecompressor(max_window_size=...)`` (window cap was only in subset.py).
    """
    window_log_max = max(10, math.ceil(math.log2(max(max_output_size, 1))))
    dctx = zstd.ZstdDecompressor(
        options={zstd.DecompressionParameter.window_log_max: window_log_max}
    )
    out = dctx.decompress(data, max_length=max_output_size)
    if not dctx.eof and not dctx.needs_input:
        raise ZstdError(f"decompressed output exceeds {max_output_size} bytes")
    return out
