"""
Minimum set of interfaces required to describe shards code to clients (solvers)
"""
import typing

from typing import Iterator

class Shards(typing.Protocol):
    base_url: str
    def package_records(self) -> Iterator[tuple[str, dict]]:
        """
        Yield (filename, record) tuples for all packages in visited shards.
        """
