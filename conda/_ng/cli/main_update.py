# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""CLI reimplementation for update"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from argparse import ArgumentParser, Namespace


def execute(args: Namespace, parser: ArgumentParser) -> int:
    from pathlib import Path

    from rattler import MatchSpec
    from rattler.exceptions import InvalidMatchSpecError

    from conda.base.context import context
    from conda.exceptions import ArgumentError
    from conda.history import History

    from .common import as_virtual_package, installed_packages
    from .install import install

    prefix = context.target_prefix
    if not Path(prefix).exists():
        raise ArgumentError(f"Target prefix '{prefix}' does not exist.")

    history = [
        MatchSpec(str(spec))
        for spec in History(prefix).get_requested_specs_map().values()
    ]
    installed = {
        pkg.name.normalized: pkg for pkg in installed_packages(context.target_prefix)
    }
    if args.packages:
        specs_queue = [*args.packages]
    elif str(args.update_modifier) == "update_all":
        specs_queue = list(installed)
    else:
        raise ArgumentError("Please specify at least one package name to update.")
    specs = []
    while specs_queue:
        spec_str = specs_queue.pop()
        try:
            spec = MatchSpec(spec_str, exact_names_only=False)
        except InvalidMatchSpecError as exc:
            raise ArgumentError(f"Invalid MatchSpec: {exc}") from exc
        if "*" in spec.name.normalized:
            for record_name, record in installed.items():
                if spec.matches(record):
                    specs_queue.append(record_name)
            continue
        if spec.name.normalized not in installed:
            raise ArgumentError(
                "conda update only allows updating installed packages; use conda install."
            )
        if str(spec) != spec.name.normalized:
            raise ArgumentError(
                "conda update only allows name-only specs; use conda install."
            )
        specs.append(spec)

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
        locked_packages=list(installed.values()),
        virtual_packages=virtual_packages,
        report=not context.quiet and not context.json,
        dry_run=context.dry_run,
    )

    return 0
