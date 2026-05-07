"""Minimum set of interfaces required to describe shards code to clients (solvers)"""
import typing

from collections.abc import Iterable
from typing import Iterator, Literal


class Shards(typing.Protocol):
    base_url: str

    def package_records(self) -> Iterator[tuple[str, dict]]:
        """
        Yield (filename, record) tuples for all packages in visited shards.
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
        algorithm: Literal["bfs", "pipelined"] = "bfs",
    ) -> dict[str, Shards] | None:
        """
        Retrieve a minimal subset of repodata based on root packages.

        Args:
            root_packages: Iterable of installed and requested package names
            channels: Dictionary mapping channel URLs to Channel objects
            algorithm: Traversal algorithm to use ("bfs" or "pipelined")

        Returns:
            A dictionary mapping channel URLs to Shards objects containing
            the subset of packages needed, or None if shards are unavailable
        """
