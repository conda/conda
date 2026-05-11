# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Interface to sharded repodata code.
"""

from __future__ import annotations

from conda._private.shards.subset import RepodataSubset, build_repodata_subset

from .typing import BuildRepodataSubset

# Define a minimal high-level API for shards

# Solver may take build_repodata_subset as an init parameter (see conda plugin
# types for solver definition) so that we can pass it our desired strategy or a
# mock

# When calling the solver, we check whether its __init__ has the new
# build_repodata_subset named parameter to determine whether it supports shards.

__all__ = ["RepodataSubset", "build_repodata_subset", "BuildRepodataSubset"]
