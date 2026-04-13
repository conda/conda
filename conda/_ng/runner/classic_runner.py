# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Classic conda backend for CLI-shaped :class:`InstallLikeInvocation`."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

    from rattler import PackageRecord

    from .invocation import InstallLikeInvocation
    from .types import CreateRequest, InstallRequest


class ClassicCondaRunner:
    """Delegate create/install to :func:`conda.cli.install.install`."""

    def create(self, request: CreateRequest) -> Iterable[PackageRecord]:
        raise TypeError(
            "ClassicCondaRunner only supports CLI invocations; use create_cli()"
        )

    def install(self, request: InstallRequest) -> Iterable[PackageRecord]:
        raise TypeError(
            "ClassicCondaRunner only supports CLI invocations; use install_cli()"
        )

    def create_cli(self, invocation: InstallLikeInvocation) -> Iterable[PackageRecord]:
        return self._install_like(invocation)

    def install_cli(self, invocation: InstallLikeInvocation) -> Iterable[PackageRecord]:
        return self._install_like(invocation)

    def _install_like(
        self, invocation: InstallLikeInvocation
    ) -> Iterable[PackageRecord]:
        from conda.cli.install import install

        install(invocation.args, invocation.parser, invocation.command)
        return ()


def default_classic_runner() -> ClassicCondaRunner:
    return ClassicCondaRunner()
