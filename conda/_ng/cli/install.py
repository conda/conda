# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Helpers for conda create, install, update and remove.

Create/install use :class:`conda._ng.runner.RattlerRunner`; update/remove call
``run_transaction`` until those flows adopt the runner protocol.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from conda._ng.runner import default_rattler_runner

from .planning import (
    diff_for_unlink_link_precs,
    parse_conflicts,
    solution_table,
    user_agent,
)

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

    from rattler import (
        Channel,
        GenericVirtualPackage,
        MatchSpec,
        PackageRecord,
        VirtualPackage,
    )


def install(
    specs: Iterable[str | MatchSpec],
    channels: Iterable[str | Channel],
    platform: str,
    target_prefix: str | Path | None = None,
    history: Iterable[str | MatchSpec] = (),
    user_specs: Iterable[str | MatchSpec] = (),
    locked_packages: Iterable[PackageRecord] | None = None,
    pinned_packages: Iterable[PackageRecord] | None = None,
    virtual_packages: Iterable[GenericVirtualPackage | VirtualPackage] | None = None,
    constraints: Iterable[MatchSpec] | None = None,
    dry_run: bool = False,
    report: bool = True,
    removing: bool = False,
    t0: float | None = None,
) -> Iterable[PackageRecord]:
    return default_rattler_runner().run_transaction(
        specs=specs,
        channels=channels,
        platform=platform,
        target_prefix=target_prefix,
        history=history,
        user_specs=user_specs,
        locked_packages=locked_packages,
        pinned_packages=pinned_packages,
        virtual_packages=virtual_packages,
        constraints=constraints,
        dry_run=dry_run,
        report=report,
        removing=removing,
        t0=t0,
        on_progress=None,
    )


__all__ = [
    "diff_for_unlink_link_precs",
    "install",
    "parse_conflicts",
    "solution_table",
    "user_agent",
]
