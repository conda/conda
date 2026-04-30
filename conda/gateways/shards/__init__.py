# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Interface to sharded repodata code.
"""

from _conda.shards.subset import RepodataSubset, build_repodata_subset

# Define a minimal high-level API for shards

# Figure out if we should make a class that is like SubdirData but that
# understands subsets of repodata, for conda search e.g.

# Solver may take build_repodata_subset as an init parameter (see conda plugin
# types for solver definition) so that we can pass it our desired strategy or a
# mock

# When calling the solver, we could check whether its __init__ has the new
# build_repodata_subset named parameter to determine whether it supports shards.
# Or we could define a Solver2 plugin with that feature.

__all__ = ["RepodataSubset", "build_repodata_subset"]
