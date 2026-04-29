"""
Interface to sharded repodata code.
"""

from _conda.shards.shards_subset import RepodataSubset, build_repodata_subset

__all__ = ["RepodataSubset", "build_repodata_subset"]
