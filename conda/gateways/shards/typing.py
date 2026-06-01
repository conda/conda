# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Minimal set of interfaces required to describe shards code to clients (solvers)"""

import typing
from collections.abc import Iterable, Iterator, KeysView
from typing import Literal


class Shards(typing.Protocol):
    base_url: str

    @property
    def package_names(self) -> KeysView[str]:
        """Return the names of all packages available in this shard collection."""
        ...

    def __contains__(self, package: str) -> bool:
        """Check if a package is available in this shard collection."""

    def iter_records(self) -> Iterator[tuple[str, dict]]:
        """
        Yield (filename, record) tuples for all packages in visited shards.
        """

    def iter_records_v3(self) -> Iterable[tuple[tuple[str, str], dict]]:
        """
        Yield ((key, section), record) tuples for all packages in visited
        shards.

        Section can be: "packages" for .tar.bz2 packages, "packages.conda"
        for .conda packages, "v3.whl", "v3.conda", "v3.tar.bz2" for v3 packages.

        key is the same as the filename for "packages", "packages.conda" but is
        different from the filename for v3 packages.
        """


class BuildRepodataSubset(typing.Protocol):
    """
    Protocol for build_repodata_subset callable.

    This function is used by solvers to construct a minimal subset of repodata
    based on the root packages that might be installed and the available channels.
    It traverses package dependencies to discover all reachable (channel, package)
    tuples, which are then used by the solver to reduce search space.
    """

    def __call__(
        self,
        root_packages: Iterable[str],
        channels: dict[str, typing.Any],
        algorithm: Literal["bfs", "pipelined"] = "pipelined",
        repodata_version: int = 1,
    ) -> dict[str, Shards] | None:
        """
        Retrieve a minimal subset of repodata based on root packages.

        Args:
            root_packages: Iterable of installed and requested package names
            channels: Dictionary mapping channel URLs to Channel objects
            algorithm: Traversal algorithm to use ("bfs" or "pipelined")
            repodata_version: repodata format version (1 = classic, 3 = v3).
        Returns:
            A dictionary mapping channel URLs to Shards objects containing
            the subset of packages needed, or None if shards are unavailable
        """
