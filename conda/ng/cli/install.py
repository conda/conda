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
    t0: float | None = None,
) -> Iterable[PackageRecord]:
    import asyncio
    import time
    from datetime import timedelta

    from rattler import Gateway, MatchSpec, solve
    from rattler import install as rattler_install
    from rattler.exceptions import GatewayError, SolverError

    from conda.exceptions import CondaError, CondaExitZero, DryRunExit
    from conda.reporters import confirm_yn

    from .common import cache_dir, create_console, installed_packages
    from .exceptions import CondaSolverError

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

    console = create_console()

    t0 = t0 or time.perf_counter()
    with console.status("solving"):
        try:
            records = asyncio.run(inner_solve())
        except SolverError as exc:
            raise CondaSolverError(str(exc)) from exc
        except GatewayError as exc:
            raise CondaError(f"Connection error:\n\n{exc}") from exc
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
        await rattler_install(
            records=records,
            target_prefix=target_prefix,
            installed_packages=installed or installed_packages(target_prefix),
            cache_dir=cache_dir("pkgs"),
            execute_link_scripts=True,
            # TODO: Fix the need to pass the inner PyMatchSpec
            requested_specs=[s._match_spec for s in specs],
            show_progress=report,
        )

    asyncio.run(inner_install())
    if report:
        print()
    return records


def parse_conflicts(
    problems: str,
    conflicts: None | dict[str, MatchSpec] = None,
    installed: Iterable[PackageRecord] = (),
) -> dict[str, list[MatchSpec]]:
    from rattler import MatchSpec

    from conda import CondaError

    unsatisfiable = {}
    not_found = {}
    for line in problems.splitlines():
        for char in "─│└├":
            line = line.replace(char, "")
        line = line.strip()
        if line.startswith("Cannot solve the request because of:"):
            line = line.split(":", 1)[1]
        words = line.split()
        if "is locked, but another version is required as reported above" in line:
            unsatisfiable[words[0]] = MatchSpec(f"{words[0]} {words[1]}")
        elif "which cannot be installed because there are no viable options" in line:
            unsatisfiable[words[0]] = MatchSpec(f"{words[0]} {words[1].strip(',')}")
        elif "cannot be installed because there are no viable options" in line:
            unsatisfiable[words[0]] = MatchSpec(f"{words[0]} {words[1]}")
        elif "the constraint" in line and "cannot be fulfilled" in line:
            unsatisfiable[words[2]] = MatchSpec(" ".join(words[2:-3]))
        elif (
            "can be installed with any of the following options" in line
            and "which" not in line
        ):
            position = line.index(" can be installed with")
            unsatisfiable[words[0]] = MatchSpec(line[:position])
        elif "No candidates were found for" in line:
            position = line.index("No candidates were found for ")
            position += len("No candidates were found for ")
            spec = line[position:].rstrip(".")
            spec = MatchSpec(spec)
            # Do not consider "not found" if it's already installed; this happens
            # when user requested a package from a channel that is no longer in the
            # list. e.g. `conda create main::psutil` + `conda install -c conda-forge python`
            if any(spec.match(record) for record in installed.values()):
                unsatisfiable[spec.name] = spec
            else:
                not_found[spec.name] = spec

    if not unsatisfiable and not_found:
        raise CondaError(f"Could not find any matches for: {not_found.values()}")

    previous = conflicts or {}
    previous_set = set(previous.values())
    current_set = set(unsatisfiable.values())

    diff = current_set.difference(previous_set)
    if len(diff) > 1 and "python" in unsatisfiable:
        # Only report python as conflict if it's the only conflict reported
        # This helps us prioritize neutering for other dependencies first
        unsatisfiable.pop("python")

    if (previous and (previous_set == current_set)) or len(diff) >= 10:
        # We have same or more (up to 10) unsatisfiable now! Abort to avoid recursion
        exc = CondaError(problems)
        raise exc

    return unsatisfiable


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
