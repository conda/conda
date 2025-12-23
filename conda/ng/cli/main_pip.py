"""CLI reimplementation for pip"""

from __future__ import annotations

from typing import TYPE_CHECKING

from conda import CondaError

if TYPE_CHECKING:
    from argparse import ArgumentParser, Namespace


def execute(args: Namespace, parser: ArgumentParser) -> int:
    raise CondaError("Not implemented yet")
