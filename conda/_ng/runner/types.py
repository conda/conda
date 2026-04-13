# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Typed requests and progress events for the package-environment runner façade."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence
    from pathlib import Path

    from rattler import (
        Channel,
        GenericVirtualPackage,
        MatchSpec,
        PackageRecord,
        PrefixRecord,
        RepoDataRecord,
        VirtualPackage,
    )

ProgressCallback = Callable[["ProgressEvent"], None]


@dataclass(frozen=True)
class SolveStarted:
    """Solver work has begun."""


@dataclass(frozen=True)
class SolveFinished:
    record_count: int
    duration_seconds: int
    duration_ms: float


@dataclass(frozen=True)
class SolutionPlanReady:
    records: tuple[RepoDataRecord, ...]
    specs: tuple[MatchSpec, ...]
    history: tuple[MatchSpec, ...]
    installed: tuple[PrefixRecord, ...]
    removing: bool


@dataclass(frozen=True)
class AwaitingConfirmation:
    prefix: str | Path


@dataclass(frozen=True)
class TransactionStarted:
    """Download/link work has begun."""


@dataclass(frozen=True)
class TransactionFinished:
    """Download/link work has completed."""


ProgressEvent = (
    SolveStarted
    | SolveFinished
    | SolutionPlanReady
    | AwaitingConfirmation
    | TransactionStarted
    | TransactionFinished
)


@dataclass
class CreateRequest:
    specs: Sequence[MatchSpec]
    channels: Sequence[str | Channel]
    platform: str
    target_prefix: str | Path
    virtual_packages: Sequence[GenericVirtualPackage | VirtualPackage] | None = None
    dry_run: bool = False
    report: bool = True
    on_progress: ProgressCallback | None = None
    constraints: Sequence[MatchSpec] | None = None
    pinned_packages: Sequence[PackageRecord] | None = None


@dataclass
class InstallRequest:
    specs: Sequence[MatchSpec]
    history: Sequence[MatchSpec]
    locked_packages: Sequence[PackageRecord] | None
    channels: Sequence[str | Channel]
    platform: str
    target_prefix: str | Path
    virtual_packages: Sequence[GenericVirtualPackage | VirtualPackage] | None = None
    dry_run: bool = False
    report: bool = True
    on_progress: ProgressCallback | None = None
    constraints: Sequence[MatchSpec] | None = None
    pinned_packages: Sequence[PackageRecord] | None = None


def merge_specs_for_solve(
    history: Iterable[MatchSpec],
    specs: Iterable[MatchSpec],
) -> list[MatchSpec]:
    """Merge history then user specs by normalized package name (conda-ng behavior)."""
    from rattler import MatchSpec

    history = [MatchSpec(spec) if isinstance(spec, str) else spec for spec in history]
    specs = [MatchSpec(spec) if isinstance(spec, str) else spec for spec in specs]
    aggregated: dict[str, MatchSpec] = {s.name.normalized: s for s in history}
    aggregated.update({s.name.normalized: s for s in specs})
    return list(aggregated.values())
