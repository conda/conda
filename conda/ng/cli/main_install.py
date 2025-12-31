# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""CLI reimplementation for install"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from argparse import ArgumentParser, Namespace


def execute(args: Namespace, parser: ArgumentParser) -> int:
    from pathlib import Path

    from rattler import MatchSpec

    from conda.base.context import context
    from conda.exceptions import ArgumentError
    from conda.history import History

    from .common import as_virtual_package, installed_packages
    from .install import install

    prefix = context.target_prefix
    if not Path(prefix).exists():
        raise ArgumentError(f"Target prefix '{prefix}' does not exist. Use 'create'?")

    history = [
        MatchSpec(str(spec))
        for spec in History(prefix).get_requested_specs_map().values()
    ]
    specs = [MatchSpec(spec) for spec in args.packages]
    virtual_packages = [
        as_virtual_package(pkg)
        for pkg in context.plugin_manager.get_virtual_package_records()
    ]
    install(
        specs=specs,
        history=history,
        channels=context.channels,
        platform=context.subdir,
        target_prefix=prefix,
        locked_packages=installed_packages(context.target_prefix),
        virtual_packages=virtual_packages,
        report=not context.quiet and not context.json,
        dry_run=context.dry_run,
    )
    History(prefix).write_specs(update_specs=map(str, specs))

    return 0
