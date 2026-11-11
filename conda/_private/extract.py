# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Lean package extraction helpers for subprocess workers."""

from __future__ import annotations

import os
import pickle

# This module is imported in each spawned extraction worker. Keep top-level
# imports limited to the standard library so loading the worker stays cheap.


def extract_conda_package_archive(
    source_full_path: str | os.PathLike,
    destination_directory: str | os.PathLike,
    *,
    ensure_picklable_errors: bool = False,
) -> None:
    """Extract a conda package archive with standard file-operation retries.

    Args:
        source_full_path: Package archive to extract.
        destination_directory: Directory to extract into.
        ensure_picklable_errors: Replace exceptions that cannot survive a pickle
            round trip with a plain ``RuntimeError``.
    """
    import conda_package_handling.api

    from ..gateways.disk import exp_backoff_fn

    try:
        exp_backoff_fn(
            conda_package_handling.api.extract,
            os.fspath(source_full_path),
            dest_dir=os.fspath(destination_directory),
        )
    except Exception as error:
        if not ensure_picklable_errors:
            raise
        try:
            # Some exceptions can be serialized but not reconstructed.
            pickle.loads(pickle.dumps(error))
        except Exception:
            error_type = f"{type(error).__module__}.{type(error).__qualname__}"
            raise RuntimeError(f"{error_type}: {error}") from None
        raise
