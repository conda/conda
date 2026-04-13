# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Construct runner requests from CLI-ready inputs (testable without argparse)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .types import CreateRequest, InstallRequest

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from rattler import (
        Channel,
        GenericVirtualPackage,
        MatchSpec,
        PackageRecord,
        VirtualPackage,
    )

    from .types import ProgressCallback


def build_create_request(
    *,
    specs: Sequence[MatchSpec],
    channels: Sequence[str | Channel],
    platform: str,
    target_prefix: str | Path,
    virtual_packages: Sequence[GenericVirtualPackage | VirtualPackage] | None,
    dry_run: bool,
    report: bool,
    on_progress: ProgressCallback | None = None,
) -> CreateRequest:
    return CreateRequest(
        specs=specs,
        channels=channels,
        platform=platform,
        target_prefix=target_prefix,
        virtual_packages=virtual_packages,
        dry_run=dry_run,
        report=report,
        on_progress=on_progress,
    )


def build_install_request(
    *,
    specs: Sequence[MatchSpec],
    history: Sequence[MatchSpec],
    locked_packages: Sequence[PackageRecord] | None,
    channels: Sequence[str | Channel],
    platform: str,
    target_prefix: str | Path,
    virtual_packages: Sequence[GenericVirtualPackage | VirtualPackage] | None,
    dry_run: bool,
    report: bool,
    on_progress: ProgressCallback | None = None,
) -> InstallRequest:
    return InstallRequest(
        specs=specs,
        history=history,
        locked_packages=locked_packages,
        channels=channels,
        platform=platform,
        target_prefix=target_prefix,
        virtual_packages=virtual_packages,
        dry_run=dry_run,
        report=report,
        on_progress=on_progress,
    )
