# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""CLI reimplementation for search"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from argparse import ArgumentParser, Namespace
    from collections.abc import Iterable

    from rattler import RepoDataRecord
    from rich.table import Table


def execute(args: Namespace, parser: ArgumentParser) -> int:
    """
    The search command does a few things:

    - Search remote channels
    - Search existing environments for installed packages
    """
    import asyncio
    import itertools

    from rattler.platform import Platform
    from rattler.repo_data import Gateway
    from rich.console import Console

    from conda.base.context import context
    from conda.exceptions import ArgumentError, PackagesNotFoundError

    from .common import cache_dir

    if args.match_spec in (None, "*"):
        raise ArgumentError("Must provide one SPEC to search.")

    specs = [args.match_spec]
    platform = args.subdir or context.subdir
    if args.override_channels:
        channels = args.channel
    else:
        channels = args.channel or list(map(str, context.channels))

    if not channels:
        raise ArgumentError("Must provide at least one channel to search.")

    platform = Platform(platform)
    if "defaults" in channels:
        defaults_idx = channels.index("defaults")
        channels = [
            *channels[:defaults_idx],
            "https://repo.anaconda.com/pkgs/main",
            "https://repo.anaconda.com/pkgs/r",
            *(("https://repo.anaconda.com/pkgs/msys2",) if platform.is_windows else ()),
            *channels[defaults_idx + 1 :],
        ]

    console = Console()
    with console.status("Searching..."):
        if args.envs:
            result = search_in_environments(args.match_spec)
        else:
            # Remote channel search
            async def inner() -> Iterable[RepoDataRecord]:
                gateway = Gateway(cache_dir=cache_dir())
                return itertools.chain(
                    *await gateway.query(
                        channels or ["conda-forge"],
                        [platform, "noarch"],
                        specs,
                        recursive=False,
                    )
                )

            result = asyncio.run(inner())

    records = sorted(result, key=lambda r: (r.name, r.version, r.build_number, r.build))
    if not records:
        raise PackagesNotFoundError(specs, channels)

    if args.info:
        for record in records:
            console.print(record_as_details(record))
    else:
        console.print(records_as_table(records))

    return 0


def records_as_table(records: Iterable[RepoDataRecord]) -> Table:
    from rich.table import Column, Table

    from .common import channel_name_or_url

    with_environment = hasattr(records[0], "installed_in_prefix")

    table = Table(
        "Name",
        Column("Version", justify="right"),
        Column("Build", justify="right"),
        "Channel",
        "Subdir",
        *(("Environment",) if with_environment else ()),
    )
    count = 0
    for record in records:
        count += 1
        table.add_row(
            record.name.normalized,
            str(record.version),
            record.build,
            channel_name_or_url(record.channel),
            record.subdir,
            *((str(record.installed_in_prefix),) if with_environment else ()),
        )
    table.caption = f"Found {count} records."
    return table


def record_as_details(record: RepoDataRecord):
    from rattler import MatchSpec
    from rich.table import Table

    from conda.common.io import dashlist
    from conda.utils import human_bytes

    table = Table()
    table.add_column("File name", justify="right")
    table.add_column(record.file_name, justify="left")
    if prefix := getattr(record, "installed_in_prefix", None):
        table.add_row("environment", str(prefix))
    table.add_row("name", record.name.normalized)
    table.add_row("version", str(record.version))
    table.add_row("build", record.build)
    table.add_row("build number", str(record.build_number))
    table.add_row("size", str(human_bytes(record.size)))
    table.add_row("license", record.license)
    table.add_row("subdir", record.subdir)
    table.add_row("url", record.url)
    table.add_row("md5", record.md5.hex())
    table.add_row("sha2566", record.sha256.hex())
    table.add_row("timestamp", str(record.timestamp))
    if record.track_features:
        table.add_section()
        table.add_row(
            "track_features", dashlist(sorted(record.track_features), indent=0).lstrip()
        )
    if record.depends:
        table.add_section()
        table.add_row(
            "dependencies",
            dashlist(
                sorted(record.depends, key=lambda s: MatchSpec(s).name.normalized),
                indent=0,
            ).lstrip(),
        )
    if record.constrains:
        table.add_section()
        table.add_row(
            "constraints",
            dashlist(
                sorted(record.constrains, key=lambda s: MatchSpec(s).name.normalized),
                indent=0,
            ).lstrip(),
        )
    return table


def search_in_environments(spec: str) -> Iterable[RepoDataRecord]:
    from pathlib import Path

    from rattler import MatchSpec
    from rattler.prefix import PrefixRecord

    from conda.core.envs_manager import list_all_known_prefixes

    spec = MatchSpec(spec)
    for prefix in list_all_known_prefixes():
        prefix = Path(prefix)
        for record_json in (prefix / "conda-meta").glob("*.json"):
            record = PrefixRecord.from_path(record_json)
            if record.matches(spec):
                record.installed_in_prefix = prefix
                yield record
