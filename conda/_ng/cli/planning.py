# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Solve-plan helpers and display (shared by install path and rattler runner)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

    from rattler import (
        MatchSpec,
        PackageRecord,
        PrefixRecord,
        RepoDataRecord,
    )


def parse_conflicts(
    problems: str,
    conflicts: None | dict[str, MatchSpec] = None,
    installed: Iterable[PackageRecord] = (),
) -> dict[str, list[MatchSpec]]:
    from rattler import MatchSpec

    from conda import CondaError

    unsatisfiable = {}
    not_found = {}
    installed_records = installed.values() if isinstance(installed, dict) else installed
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
            if any(spec.match(record) for record in installed_records):
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
        unsatisfiable.pop("python")

    if (previous and (previous_set == current_set)) or len(diff) >= 10:
        exc = CondaError(problems)
        raise exc

    return unsatisfiable


def _install_plan_table_shell():
    from rich.table import Column

    from .common import create_table

    return create_table(
        "*",
        "Name",
        "Version",
        Column("Build", justify="right"),
        "Channel",
        "Subdir",
        "Requested as",
        caption_justify="left",
    )


def solution_install_plan_rows(
    records: Iterable[RepoDataRecord],
    specs: Iterable[MatchSpec] = (),
    history: Iterable[MatchSpec] = (),
    installed: Iterable[PrefixRecord] = (),
    removing: bool = False,
) -> tuple[list[dict[str, str]], str | None]:
    """Row dicts shared by the console reporter and :func:`solution_table`."""
    from .common import channel_name_or_url

    rows: list[dict[str, str]] = []
    installed = {record.name.normalized: record for record in installed}
    records = {record.name.normalized: record for record in records}
    all_names = sorted(dict.fromkeys([*installed, *records]))
    for name in all_names:
        requested = [spec for spec in specs if spec.name.normalized == name]
        historic = [spec for spec in history if spec.name.normalized == name]

        styles: list[str] = []
        if not removing:
            if historic:
                styles.append("blue")
            if requested:
                styles.append("bold")
        requested_or_historic_spec = " & ".join(
            [str(s) for s in (requested or historic)]
        )

        if name in installed and name in records:
            installed_record = installed[name]
            record = records[name]
            if installed_record.sha256 == record.sha256:
                status = ""
                styles.append("dim")
            else:
                styles.append("green")
                status = "+"
                rows.append(
                    {
                        "status": "-",
                        "name": installed_record.name.normalized,
                        "version": str(installed_record.version),
                        "build": installed_record.build,
                        "channel": channel_name_or_url(installed_record.channel),
                        "subdir": installed_record.subdir,
                        "requested": "",
                        "style": ("red bold" if removing or requested else "red dim"),
                    }
                )
        elif name in records and name not in installed:
            status = "+"
            styles.append("green")
        elif name in installed and name not in records:
            status = "-"
            styles.extend(["red", "bold" if removing else "dim"])
        record = records.get(name) or installed[name]
        rows.append(
            {
                "status": status,
                "name": record.name.normalized,
                "version": str(record.version),
                "build": record.build,
                "channel": channel_name_or_url(record.channel),
                "subdir": record.subdir,
                "requested": requested_or_historic_spec,
                "style": " ".join(styles),
            }
        )
    caption = None
    if not removing:
        caption = "Legend: bold=requested, green=added, red=removed, blue=historic"
    return rows, caption


def build_install_plan_table(
    rows: Iterable[dict[str, str]], *, caption: str | None = None
):
    """Build the Rich table used for classic and rattler plan display."""
    table = _install_plan_table_shell()
    for r in rows:
        table.add_row(
            r.get("status", ""),
            r["name"],
            r["version"],
            r["build"],
            r["channel"],
            r["subdir"],
            r.get("requested", ""),
            style=r.get("style", ""),
        )
    if caption:
        table.caption = caption
    return table


def solution_table(
    records: Iterable[RepoDataRecord],
    specs: Iterable[MatchSpec] = (),
    history: Iterable[MatchSpec] = (),
    installed: Iterable[PrefixRecord] = (),
    removing: bool = False,
):
    rows, caption = solution_install_plan_rows(
        records, specs=specs, history=history, installed=installed, removing=removing
    )
    return build_install_plan_table(rows, caption=caption)


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

    def _add_to_unlink_and_link(rec: PackageRecord) -> None:
        link_precs.add(rec)
        if rec in previous_set:
            unlink_precs.add(rec)

    if force_reinstall:
        for spec in specs_to_add:
            prec = next((rec for rec in new_records if spec.matches(rec)), None)
            if not prec:
                raise RuntimeError(f"Could not find record for spec {spec}")
            _add_to_unlink_and_link(prec)

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
