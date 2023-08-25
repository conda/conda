# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Backport of conda.core.package_cache_data for conda-build."""
from ..deprecations import deprecated
from .package_cache_data import ProgressiveFetchExtract

deprecated.module(
    "24.3", "24.9", addendum="Use `conda.core.package_cache_data` instead."
)

ProgressiveFetchExtract = ProgressiveFetchExtract
