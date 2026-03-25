# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""CLI reimplementation for remove"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from argparse import ArgumentParser, Namespace


def execute(args: Namespace, parser: ArgumentParser) -> int:
    import time
    from pathlib import Path

    from rattler import MatchSpec
    from rattler.exceptions import InvalidMatchSpecError

    from conda.base.context import context
    from conda.exceptions import ArgumentError
    from conda.history import History

    from .common import as_virtual_package, installed_packages
    from .exceptions import CondaSolverError
    from .install import install, parse_conflicts

    prefix = context.target_prefix
    if not Path(prefix).exists():
        raise ArgumentError(f"Target prefix '{prefix}' does not exist.")

    history = [
        MatchSpec(str(spec))
        for spec in History(prefix).get_requested_specs_map().values()
    ]
    installed = {
        record.name.normalized: record for record in installed_packages(prefix)
    }
    if args.package_names:
        try:
            names = [
                MatchSpec(spec, exact_names_only=False) for spec in args.package_names
            ]
        except InvalidMatchSpecError as exc:
            raise ArgumentError(f"Invalid MatchSpec: {exc}") from exc
    elif args.all:
        names = [MatchSpec(name) for name in installed]
    else:
        raise ArgumentError("Please specify at least one package to remove.")
    virtual_packages = [
        as_virtual_package(pkg)
        for pkg in context.plugin_manager.get_virtual_package_records()
    ]

    # conda remove allows globbed names; make sure we don't install those!
    remove = set()
    for spec in names:
        if "*" in spec.name.normalized:
            for record_name, record in installed.items():
                if spec.matches(record):
                    remove.add(record_name)
        elif spec.name.normalized not in installed:
            raise ArgumentError(
                f"Package '{spec}' is not installed. Nothing to remove."
            )
        else:
            remove.add(spec.name.normalized)
    if not remove:
        raise ArgumentError("Passed specs did not match any installed packages.")

    remove_depends = set()
    for spec in history:
        installed_history = installed[spec.name.normalized]
        for dep in installed_history.depends:
            dep_spec = MatchSpec(dep)
            if dep_spec.name.normalized in remove:
                remove_depends.add(spec.name.normalized)

    if args.force_remove:
        from rattler import install as rattler_install

        from conda.reporters import confirm_yn

        from .common import cache_dir, create_console
        from .install import solution_table

        records = [rec for name, rec in installed.items() if name not in remove]
        n_pkgs = len(installed) - len(records)
        if not context.quiet and not context.json:
            create_console().print(
                solution_table(
                    records=records,
                    specs=names,
                    history=history,
                    installed=installed.values(),
                    removing=True,
                ),
                "",
            )

        confirm_yn(
            f"Force removing {n_pkgs} package(s). "
            "Environment may be left unusable. Proceed?",
            dry_run=context.dry_run,
        )

        rattler_install(
            records,
            target_prefix=prefix,
            cache_dir=cache_dir("pkgs"),
            installed_packages=installed.values(),
            show_progress=not context.quiet and not context.json,
            execute_link_scripts=True,
        )
        return 0

    conflicts = {}
    t0 = time.perf_counter()
    last_exception = None
    for _ in range(1, 6):
        try:
            conflicting_names = set(conflicts.keys())
            specs = [
                spec
                for spec in history
                if spec.name.normalized
                not in remove | remove_depends | conflicting_names
            ]
            install(
                specs=specs,
                user_specs=names,
                history=(),
                channels=context.channels,
                platform=context.subdir,
                target_prefix=prefix,
                locked_packages=[
                    record
                    for record_name, record in installed.items()
                    if record_name not in remove | remove_depends | conflicting_names
                ],
                virtual_packages=virtual_packages,
                constraints=[f"{name}<0.0dev0" for name in remove],
                report=not context.quiet and not context.json,
                dry_run=context.dry_run,
                removing=True,
                t0=t0,
            )
        except CondaSolverError as exc:
            last_exception = exc
            new_conflicts = parse_conflicts(
                str(exc), conflicts=conflicts, installed=installed.values()
            )
            conflicts.update(new_conflicts)
        else:
            break
    else:
        if last_exception:
            raise last_exception

    History(prefix).write_specs(remove_specs=names)

    return 0
