# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Shared ``conda create`` / ``conda install`` dispatch behind ``context.experimental``.

Enable with ``experimental`` list entries (``condarc`` or env):

- ``shared_cli_rattler`` — run :class:`~conda._ng.runner.rattler_runner.RattlerRunner`
- ``shared_cli_classic`` — run :class:`~conda._ng.runner.classic_runner.ClassicCondaRunner`

Rattler path supports plain package specs only (no ``--file``, no ``--clone`` for create).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .invocation import invocation_from_install_like

if TYPE_CHECKING:
    from argparse import ArgumentParser, Namespace
    from collections.abc import Iterable
    from typing import Literal

    from rattler import PackageRecord

    from .invocation import CommandLiteral

SHARED_CLI_RATTLER = "shared_cli_rattler"
SHARED_CLI_CLASSIC = "shared_cli_classic"


def shared_cli_engine() -> Literal["rattler", "classic"] | None:
    """Which shared runner engine is active, or ``None`` to use legacy ``install()`` only."""
    from conda.base.context import context

    experimental = tuple(context.experimental)
    if SHARED_CLI_RATTLER in experimental:
        return "rattler"
    if SHARED_CLI_CLASSIC in experimental:
        return "classic"
    return None


def shared_cli_create_supported(args: Namespace) -> bool:
    """Whether ``conda create`` can use the rattler shared path for this argv."""
    if getattr(args, "clone", None):
        return False
    if getattr(args, "file", None):
        return False
    if not (args.packages or ()):
        return False
    return True


def shared_cli_install_supported(args: Namespace) -> bool:
    """Whether ``conda install`` can use the rattler shared path for this argv."""
    if getattr(args, "revision", None):
        return False
    if getattr(args, "file", None):
        return False
    if not (args.packages or ()):
        return False
    return True


def dispatch_install_like(
    args: Namespace,
    parser: ArgumentParser,
    command: CommandLiteral,
) -> Iterable[PackageRecord]:
    """
    Run the selected runner for a create/install-like command.

    Call only after classic ``execute`` has validated argv and refreshed ``context``.
    """
    from .classic_runner import ClassicCondaRunner
    from .rattler_runner import RattlerRunner

    engine = shared_cli_engine()
    if engine is None:
        raise RuntimeError(
            "dispatch_install_like called without shared CLI experimental flag"
        )

    inv = invocation_from_install_like(args, parser, command)
    if engine == "classic":
        runner: ClassicCondaRunner | RattlerRunner = ClassicCondaRunner()
    else:
        runner = RattlerRunner()

    if command == "create":
        return runner.create_cli(inv)
    return runner.install_cli(inv)
