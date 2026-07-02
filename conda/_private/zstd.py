# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Internal zstd backend selector.

Import ``zstd`` for library API (``zstd.ZstdFile``, ``zstd.compress``, …).
Import ``ZstdError`` for exception handling.
Import ``capped_decompress`` for bounded one-shot decompression of untrusted data (mimics
         ``zstandard.decompress(..., max_output_size=...)`` and
         ``ZstdDecompressor(max_window_size=...)``).
"""

from __future__ import annotations

import math
import sys

if sys.version_info >= (3, 14):
    import compression.zstd as _zstd
    from compression.zstd import ZstdError, ZstdFile, compress, decompress
else:
    import backports.zstd as _zstd
    from backports.zstd import ZstdError, ZstdFile, compress, decompress

__all__ = [
    "capped_decompress",
    "compress",
    "decompress",
    "ZstdError",
    "ZstdFile",
]


def capped_decompress(data: bytes, max_output_size: int) -> bytes:
    """One-shot decompress of untrusted data with output and window bounds.

    Replaces ``zstandard.decompress(..., max_output_size=...)`` and
    ``ZstdDecompressor(max_window_size=...)`` (window cap was only in subset.py).
    """
    window_log_max = max(10, math.ceil(math.log2(max(max_output_size, 1))))
    dctx = _zstd.ZstdDecompressor(
        options={_zstd.DecompressionParameter.window_log_max: window_log_max}
    )
    out = dctx.decompress(data, max_length=max_output_size)
    if not dctx.eof and not dctx.needs_input:
        raise ZstdError(f"decompressed output exceeds {max_output_size} bytes")
    return out
