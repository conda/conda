# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Helpers for conda create, install, update and remove.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

    from rattler import (
        Channel,
        GenericVirtualPackage,
        MatchSpec,
        PackageRecord,
        PrefixRecord,
        RepoDataRecord,
        VirtualPackage,
    )


def install(
    specs: Iterable[str | MatchSpec],
    channels: Iterable[str | Channel],
    platform: str,
    target_prefix: str | Path | None = None,
    history: Iterable[str | MatchSpec] = (),
    locked_packages: Iterable[PackageRecord] | None = None,
    pinned_packages: Iterable[PackageRecord] | None = None,
    virtual_packages: Iterable[GenericVirtualPackage | VirtualPackage] | None = None,
    constraints: Iterable[MatchSpec] | None = None,
    dry_run: bool = False,
    report: bool = True,
    removing: bool = False,
) -> None:
    import asyncio
    import time
    from datetime import timedelta

    from rattler import Gateway, MatchSpec, install, solve
    from rattler.exceptions import SolverError
    from rich.console import Console

    from conda.exceptions import CondaError, CondaExitZero, DryRunExit
    from conda.reporters import confirm_yn

    from .common import cache_dir

    specs = [MatchSpec(spec) if isinstance(spec, str) else spec for spec in specs]
    history = [MatchSpec(spec) if isinstance(spec, str) else spec for spec in history]
    aggregated_specs = {spec.name.normalized: spec for spec in history}
    aggregated_specs.update({spec.name.normalized: spec for spec in specs})

    async def inner_solve():
        gateway = Gateway(cache_dir=cache_dir("index"), show_progress=report)
        return await solve(
            channels,
            specs=aggregated_specs.values(),
            gateway=gateway,
            platforms=[platform, "noarch"],
            locked_packages=locked_packages,
            pinned_packages=pinned_packages,
            virtual_packages=virtual_packages,
            constraints=constraints,
        )

    console = Console()

    t0 = time.perf_counter()
    with console.status("solving"):
        try:
            records = asyncio.run(inner_solve())
        except SolverError as exc:
            raise CondaError(f"Solver error:\n\n{exc}") from exc
    t1 = time.perf_counter()
    delta = timedelta(seconds=t1 - t0)
    console.print(
        f"[green]✔[/] solving [dim]{len(records)} packages in "
        f"{delta.seconds}s {delta.microseconds / 1000:.0f}ms",
        highlight=False,
    )

    if target_prefix:
        installed = installed_packages(target_prefix)
        if set(record.sha256 for record in installed) == set(
            record.sha256 for record in records
        ):
            raise CondaExitZero("Nothing to do.")
    else:
        installed = ()
    if not installed and not records:
        raise CondaExitZero("Nothing to do.")

    if report:
        console.print(
            solution_table(
                records=records,
                specs=specs,
                installed=installed,
                history=history,
                removing=removing,
            )
        )

    if dry_run:
        raise DryRunExit()

    confirm_yn(f"\nApply changes to '{target_prefix}'?")

    async def inner_install():
        await install(
            records=records,
            target_prefix=target_prefix,
            installed_packages=installed or installed_packages(target_prefix),
            cache_dir=cache_dir("pkgs"),
            # TODO: Fix the need to pass the inner PyMatchSpec
            requested_specs=[s._match_spec for s in specs],
            show_progress=report,
        )

    asyncio.run(inner_install())
    if report:
        print()


def solution_table(
    records: Iterable[RepoDataRecord],
    specs: Iterable[MatchSpec] = (),
    history: Iterable[MatchSpec] = (),
    installed: Iterable[PrefixRecord] = (),
    removing: bool = False,
):
    from rich.table import Column

    from .common import channel_name_or_url, create_table

    table = create_table(
        "*",
        "Name",
        "Version",
        Column("Build", justify="right"),
        "Channel",
        "Subdir",
        "Requested as",
        caption_justify="left",
    )
    installed = {record.name.normalized: record for record in installed}
    records = {record.name.normalized: record for record in records}
    all_names = sorted(dict.fromkeys([*installed, *records]))
    for name in all_names:
        # These are the specs for "Requested as" column
        requested = [spec for spec in specs if spec.name.normalized == name]
        historic = [spec for spec in history if spec.name.normalized == name]

        styles = []
        if not removing:
            if historic:
                styles.append("blue")
            if requested:
                styles.append("bold")
        requested_or_historic_spec = " & ".join(
            [str(s) for s in (requested or historic)]
        )

        # Table entries may have three states: added, removed or kept
        # 'added' always comes from the records list
        # 'removed' and 'kept' always come from installed; a removed
        # entry is one that is also found in added
        if name in installed and name in records:
            installed_record = installed[name]
            record = records[name]
            if installed_record.sha256 == record.sha256:
                # No change
                status = ""
                styles.append("dim")
            else:
                # There was a change!
                styles.append("green")
                status = "+"
                table.add_row(
                    "-",
                    installed_record.name.normalized,
                    str(installed_record.version),
                    installed_record.build,
                    channel_name_or_url(installed_record.channel),
                    installed_record.subdir,
                    None,
                    style="red bold" if removing or requested else "red dim",
                )
        elif name in records and name not in installed:
            status = "+"
            styles.append("green")
        elif name in installed and name not in records:
            status = "-"
            styles.extend(["red", "bold" if removing else "dim"])
        record = records.get(name) or installed[name]
        table.add_row(
            status,
            record.name.normalized,
            str(record.version),
            record.build,
            channel_name_or_url(record.channel),
            record.subdir,
            requested_or_historic_spec,
            style=" ".join(styles),
        )
    table.caption = "Legend: bold=requested, green=added, red=removed, blue=historic"
    return table


def installed_packages(prefix: Path | str, sorted: bool = True) -> list[PrefixRecord]:
    from pathlib import Path

    from rattler import PrefixRecord

    packages = [
        PrefixRecord.from_path(f) for f in Path(prefix, "conda-meta").glob("*.json")
    ]
    if sorted:
        packages.sort(key=lambda r: (r.name.normalized, r.version, r.build_number))
    return packages
