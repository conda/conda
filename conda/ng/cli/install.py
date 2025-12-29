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
    verbose: bool = False,
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
    if not records:
        raise CondaExitZero("Nothing to do.")

    if report:
        console.print(
            solution_table(
                records=records,
                specs=specs,
                installed=installed,
                history=history,
                verbose=verbose,
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
    verbose: bool = False,
):
    from rich.table import Column

    from .common import channel_name_or_url, create_table

    table = create_table(
        *(("*",) if verbose else ()),
        "Name",
        "Version",
        Column("Build", justify="right"),
        "Channel",
        "Subdir",
        *("Requested as",) if verbose else (),
        caption_justify="left",
    )
    installed = {record.name.normalized: record for record in installed}
    non_requested = 0
    for record in sorted(records, key=lambda r: r.name.normalized):
        requested = [spec for spec in specs if record.matches(spec)]
        historic = [spec for spec in history if record.matches(spec)]
        new = record.name.normalized not in installed
        removed = installed.get(record.name.normalized)
        if removed and removed.sha256 == record.sha256:
            removed = None
        styles = []
        if verbose:
            if historic:
                styles.extend(["blue"])
            if requested:
                styles.append("bold")
            else:
                styles.append("dim")
        if not requested:
            non_requested += 1
        requested_or_historic_spec = (
            (" & ".join([str(s) for s in (requested or historic)]),) if verbose else ()
        )
        if removed and verbose:
            styles.append("green")
            table.add_row(
                "-",
                removed.name.normalized,
                str(removed.version),
                removed.build,
                channel_name_or_url(removed.channel),
                removed.subdir,
                None,
                style="red dim",
            )
        if requested or verbose:
            table.add_row(
                *(("+" if new or removed else "",) if verbose else ()),
                record.name.normalized,
                str(record.version),
                record.build,
                channel_name_or_url(record.channel),
                record.subdir,
                *requested_or_historic_spec,
                style=" ".join(styles),
            )
    if verbose:
        table.caption = (
            "Legend: bold=requested, green=added, red=removed, blue=historic"
        )
    elif non_requested:
        table.caption = f"+ {non_requested} packages, use -v to show all"
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
