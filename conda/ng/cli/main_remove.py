# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""CLI reimplementation for remove"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from argparse import ArgumentParser, Namespace


def execute(args: Namespace, parser: ArgumentParser) -> int:
    import time

    from rattler import MatchSpec
    from rattler.exceptions import InvalidMatchSpecError

    from conda.base.context import context
    from conda.exceptions import ArgumentError
    from conda.history import History

    from .common import as_virtual_package, installed_packages
    from .exceptions import CondaSolverError
    from .install import install, parse_conflicts

    prefix = context.target_prefix
    history = [
        MatchSpec(str(spec))
        for spec in History(prefix).get_requested_specs_map().values()
    ]
    try:
        names = [MatchSpec(spec) for spec in args.package_names]
    except InvalidMatchSpecError as exc:
        raise ArgumentError(f"Invalid MatchSpec: {exc}") from exc
    installed = {
        record.name.normalized: record
        for record in installed_packages(context.target_prefix)
    }
    virtual_packages = [
        as_virtual_package(pkg)
        for pkg in context.plugin_manager.get_virtual_package_records()
    ]

    conflicts = {}
    t0 = time.perf_counter()
    for _ in range(1, 6):
        try:
            # conda remove allows globbed names; make sure we don't install those!
            remove = set()
            for spec in names:
                if "*" in str(spec):
                    raise ArgumentError(
                        f"Asterisks in package names are not supported yet: {spec}"
                    )
                    for record_name, record in installed.items():
                        if spec.match(record):
                            remove.add(record_name)
                elif spec not in installed:
                    raise ArgumentError(
                        f"Package '{spec}' is not installed. Nothing to remove."
                    )
                else:
                    remove.add(spec.name.normalized)
            remove_depends = set()
            for spec in history:
                installed_history = installed[spec.name.normalized]
                for dep in installed_history.depends:
                    dep_spec = MatchSpec(dep)
                    if dep_spec.name.normalized in remove:
                        remove_depends.add(spec.name.normalized)
            conflicting_names = set(conflicts.keys())
            specs = [
                spec
                for spec in history
                if spec.name.normalized
                not in remove | remove_depends | conflicting_names
            ]
            install(
                specs=specs,
                history=(),
                channels=context.channels,
                platform=context.subdir,
                target_prefix=context.target_prefix,
                locked_packages=[
                    record
                    for record_name, record in installed.items()
                    if record_name not in remove | remove_depends | conflicting_names
                ],
                virtual_packages=virtual_packages,
                constraints=[f"{name}<0.0dev0" for name in remove],
                report=True,
                dry_run=context.dry_run,
                removing=True,
                t0=t0,
            )
        except CondaSolverError as exc:
            new_conflicts = parse_conflicts(
                str(exc), conflicts=conflicts, installed=installed.values()
            )
            conflicts.update(new_conflicts)
        else:
            break
    return 0
