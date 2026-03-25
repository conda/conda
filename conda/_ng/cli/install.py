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
    user_specs: Iterable[str | MatchSpec] = (),
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

    from rattler import Client, Gateway, MatchSpec, SourceConfig, solve
    from rattler import install as rattler_install
    from rattler.exceptions import GatewayError, SolverError

    from conda.base.context import context
    from conda.exceptions import CondaError, CondaExitZero, DryRunExit
    from conda.history import History
    from conda.reporters import confirm_yn

    from .common import cache_dir, create_console, installed_packages
    from .exceptions import CondaSolverError

    specs = [MatchSpec(spec) if isinstance(spec, str) else spec for spec in specs]
    history = [MatchSpec(spec) if isinstance(spec, str) else spec for spec in history]
    aggregated_specs = {spec.name.normalized: spec for spec in history}
    aggregated_specs.update({spec.name.normalized: spec for spec in specs})

    # Networking stuff
    # Here we can configure things like user agent, request headers and authentication
    # headers = context.plugin_manager.get_session_headers()
    # headers = context.plugin_manager.get_request_headers()
    client = Client(headers={"User-Agent": user_agent()})
    gateway_config = SourceConfig(
        cache_action="force-cache-only" if context.offline else "cache-or-fetch"
    )
    gateway = Gateway(
        cache_dir=cache_dir("index"),
        client=client,
        show_progress=report,
        default_config=gateway_config,
    )

    async def inner_solve():
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

    # pre-solve
    context.plugin_manager.invoke_pre_solves(
        specs_to_add=user_specs or specs if not removing else (),
        specs_to_remove=user_specs or specs if removing else (),
    )

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
        + (f"{delta.seconds}s " if delta.seconds else "")
        + f"{delta.microseconds / 1000:.0f}ms",
        highlight=False,
    )

    if target_prefix:
        installed = list(installed_packages(target_prefix))
        if set(record.sha256 for record in installed) == set(
            record.sha256 for record in records
        ):
            raise CondaExitZero("Nothing to do.")
    else:
        installed = ()

    # post-solve
    to_unlink, to_link = diff_for_unlink_link_precs(
        previous_records=installed,
        new_records=records,
        specs_to_add=user_specs,
    )
    context.plugin_manager.invoke_post_solves("repodata.json", to_unlink, to_link)

    if not installed and not records:
        raise CondaExitZero("Nothing to do.")

    if report:
        console.print(
            "",
            solution_table(
                records=records,
                specs=specs,
                installed=installed,
                history=history,
                removing=removing,
            ),
        )

    if dry_run:
        raise DryRunExit()

    confirm_yn(f"\nApply changes to '{target_prefix}'?")

    async def inner_install():
        await rattler_install(
            records=records,
            target_prefix=target_prefix,
            installed_packages=installed or list(installed_packages(target_prefix)),
            cache_dir=cache_dir("pkgs"),
            execute_link_scripts=True,
            # TODO: Fix the need to pass the inner PyMatchSpec
            requested_specs=[s._match_spec for s in (user_specs or specs)],
            show_progress=report,
            client=client,
        )

    # pre-transaction
    txn_context = {}
    for action in context.plugin_manager.get_pre_transaction_actions(
        transaction_context=txn_context,
        target_prefix=target_prefix,
        unlink_precs=to_unlink,
        link_precs=to_link,
        remove_specs=user_specs or specs if removing else (),
        update_specs=user_specs or specs if not removing else (),
        neutered_specs=(),
    ):
        action.execute()

    # Write History ourselves, rattler doesn't do that yet
    with History(target_prefix) as h:
        asyncio.run(inner_install())
    if not removing:
        h.write_specs(update_specs=list(map(str, (user_specs or specs))))
    if report:
        print()

    # post-transaction
    for action in context.plugin_manager.get_pre_transaction_actions(
        transaction_context=txn_context,
        target_prefix=target_prefix,
        unlink_precs=to_unlink,
        link_precs=to_link,
        remove_specs=user_specs or specs if removing else (),
        update_specs=user_specs or specs if not removing else (),
        neutered_specs=(),  # TODO? Not implemented
    ):
        action.execute()

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
    if not removing:
        table.caption = (
            "Legend: bold=requested, green=added, red=removed, blue=historic"
        )
    return table


def diff_for_unlink_link_precs(
    previous_records: Iterable[PackageRecord],
    new_records: Iterable[PackageRecord],
    specs_to_add: Iterable[MatchSpec] = (),
    force_reinstall: bool = False,
) -> tuple[tuple[PackageRecord, ...], tuple[PackageRecord, ...]]:
    from rattler import MatchSpec

    previous_set = set(previous_records)
    new_set = set(new_records)
    unlink_precs = previous_set - new_set
    link_precs = new_set - previous_set

    def _add_to_unlink_and_link(rec):
        link_precs.add(rec)
        if prec in previous_records:
            unlink_precs.add(rec)

    # If force_reinstall is enabled, make sure any package in specs_to_add is unlinked then
    # re-linked
    if force_reinstall:
        for spec in specs_to_add:
            prec = next((rec for rec in new_records if spec.matches(rec)), None)
            if not prec:
                raise RuntimeError(f"Could not find record for spec {spec}")
            _add_to_unlink_and_link(prec)

    # add back 'noarch: python' packages to unlink and link if python version changes
    python_spec = MatchSpec("python")
    prev_python = next(
        (rec for rec in previous_records if python_spec.matches(rec)), None
    )
    curr_python = next((rec for rec in new_records if python_spec.matches(rec)), None)
    if (
        prev_python
        and curr_python
        and prev_python.version.as_major_minor() != curr_python.version.as_major_minor()
    ):
        noarch_python_precs = (p for p in new_records if p.noarch.python)
        for prec in noarch_python_precs:
            _add_to_unlink_and_link(prec)

    unlink_precs = sorted(
        unlink_precs, key=lambda x: previous_records.index(x), reverse=True
    )

    link_precs = sorted(link_precs, key=lambda x: new_records.index(x))
    return tuple(unlink_precs), tuple(link_precs)


def user_agent() -> str:
    import rattler

    from conda import __version__
    from conda.base.context import context

    builder = [f"conda/{__version__} conda-ng/1 py-rattler/{rattler.__version__}"]
    builder.append("{}/{}".format(*context.python_implementation_name_version))
    builder.append("{}/{}".format(*context.platform_system_release))
    builder.append("{}/{}".format(*context.os_distribution_name_version))
    if context.libc_family_version[0]:
        builder.append("{}/{}".format(*context.libc_family_version))

    return " ".join(builder)
