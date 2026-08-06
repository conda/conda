# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Lean package extraction helpers for subprocess workers."""

from __future__ import annotations

import os

# This module is imported in each spawned extraction worker. Keep top-level
# imports limited to the standard library so loading the worker stays cheap.


def extract_conda_package_archive(
    source_full_path: str | os.PathLike,
    destination_directory: str | os.PathLike,
) -> None:
    """Extract a conda package archive with standard file-operation retries."""
    import conda_package_handling.api

    from ..gateways.disk import exp_backoff_fn

    exp_backoff_fn(
        conda_package_handling.api.extract,
        os.fspath(source_full_path),
        dest_dir=os.fspath(destination_directory),
    )
