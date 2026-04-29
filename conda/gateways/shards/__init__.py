# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Interface to sharded repodata code.
"""

from _conda.shards.subset import RepodataSubset, build_repodata_subset

__all__ = ["RepodataSubset", "build_repodata_subset"]
