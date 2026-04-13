# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""CLI-shaped invocations for shared create/install dispatch."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from argparse import ArgumentParser, Namespace

CommandLiteral = Literal["create", "install"]


@dataclass
class InstallLikeInvocation:
    """Parsed ``conda create`` / ``conda install`` state for runner backends."""

    args: Namespace
    parser: ArgumentParser
    command: CommandLiteral
    target_prefix: Path
    spec_strings: tuple[str, ...]


def invocation_from_install_like(
    args: Namespace,
    parser: ArgumentParser,
    command: CommandLiteral,
) -> InstallLikeInvocation:
    """Build an invocation after ``context`` reflects the active prefix and flags."""
    from conda.base.context import context

    return InstallLikeInvocation(
        args=args,
        parser=parser,
        command=command,
        target_prefix=Path(context.target_prefix),
        spec_strings=tuple(args.packages or ()),
    )
