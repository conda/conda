# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Lean package extraction helpers for subprocess workers."""

from __future__ import annotations

import os


def extract_conda_package_archive(
    source_full_path: str | os.PathLike,
    destination_directory: str | os.PathLike,
) -> None:
    """Extract a conda package archive without importing conda runtime state."""
    import conda_package_handling.api

    conda_package_handling.api.extract(
        os.fspath(source_full_path),
        dest_dir=os.fspath(destination_directory),
    )
