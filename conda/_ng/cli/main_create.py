# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""CLI reimplementation for create"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from argparse import ArgumentParser, Namespace


def execute(args: Namespace, parser: ArgumentParser) -> int:
    from pathlib import Path

    import rich
    from rattler import MatchSpec

    from conda.base.context import context
    from conda.exceptions import ArgumentError

    from .common import activate_panel, as_virtual_package
    from .install import install

    if not args.name and not args.prefix and not context.dry_run:
        raise ArgumentError("one of the arguments -n/--name -p/--prefix is required")

    specs = [MatchSpec(spec) for spec in args.packages]
    if not specs:
        raise ArgumentError("Must pass at least one spec.")

    target_prefix = args.prefix
    if not context.dry_run and not target_prefix:
        target_prefix = Path(context.envs_dirs[0], args.name)

    if not context.dry_run and Path(target_prefix).exists():
        raise ArgumentError(f"Target prefix '{target_prefix}' already exists.")

    virtual_packages = [
        as_virtual_package(pkg)
        for pkg in context.plugin_manager.get_virtual_package_records()
    ]
    install(
        specs=specs,
        channels=context.channels,
        platform=context.subdir,
        target_prefix=target_prefix,
        virtual_packages=virtual_packages,
        report=not context.quiet and not context.json,
        dry_run=context.dry_run,
    )

    if not context.quiet and not context.json:
        rich.print(activate_panel(args.name or target_prefix))

    return 0
