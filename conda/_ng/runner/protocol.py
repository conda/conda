# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Protocol for create/install backends (e.g. py-rattler vs classic conda)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Iterable

    from rattler import PackageRecord

    from .invocation import InstallLikeInvocation
    from .types import CreateRequest, InstallRequest


class PackageEnvironmentRunner(Protocol):
    """Engine behind ``CreateRequest`` / ``InstallRequest`` or CLI invocations."""

    def create(self, request: CreateRequest) -> Iterable[PackageRecord]:
        """Solve and apply packages for a new prefix (programmatic API)."""

    def install(self, request: InstallRequest) -> Iterable[PackageRecord]:
        """Solve and apply packages into an existing prefix (programmatic API)."""

    def create_cli(self, invocation: InstallLikeInvocation) -> Iterable[PackageRecord]:
        """Same as ``create`` using parsed ``conda create`` argv."""

    def install_cli(self, invocation: InstallLikeInvocation) -> Iterable[PackageRecord]:
        """Same as ``install`` using parsed ``conda install`` argv."""
