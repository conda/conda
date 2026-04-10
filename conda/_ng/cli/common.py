# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Common utilities for the CLI layer.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable
    from typing import Literal

    from rattler import GenericVirtualPackage, PackageRecord, PrefixRecord
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table


def cache_dir(kind: Literal["pkgs", "index"] = "pkgs") -> Path:
    from conda.base.context import context

    for pkgs_dir in context.pkgs_dirs:
        if kind == "index":
            return Path(pkgs_dir, "cache")
        return Path(pkgs_dir)


def activate_panel(env_name_or_prefix) -> Panel:
    from rich.panel import Panel

    from conda.auxlib.ish import dals

    if " " in env_name_or_prefix:
        env_name_or_prefix = f'"{env_name_or_prefix}"'
    message = dals(
        f"""
        To activate this environment, use:

            $ conda activate {env_name_or_prefix}

        To deactivate an active environment, use:

            $ conda deactivate"""
    )
    return Panel(message, title="Activation instructions", expand=False, padding=1)


def create_console(*args, **kwargs) -> Console:
    import sys

    from rich.console import Console

    kwargs.setdefault("soft_wrap", True)
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        # Disable output trimming in non-interactive sessions
        kwargs.setdefault("width", 100_000)
    return Console(*args, **kwargs)


def create_table(*columns, **kwargs) -> Table:
    from rich import box
    from rich.table import Table

    kwargs.setdefault("show_edge", False)
    kwargs.setdefault("show_header", True)
    kwargs.setdefault("show_footer", True)
    kwargs.setdefault("expand", False)
    kwargs.setdefault("box", box.SIMPLE)

    return Table(*columns, **kwargs)


def as_virtual_package(record) -> GenericVirtualPackage:
    from rattler import GenericVirtualPackage, PackageName, Version

    return GenericVirtualPackage(
        PackageName(record.name), Version(record.version), record.build
    )


def channel_name_or_url(url: str, full_url: bool = False) -> str:
    from conda.base.constants import KNOWN_SUBDIRS
    from conda.base.context import context

    if url.endswith(tuple(f"/{subdir}" for subdir in KNOWN_SUBDIRS)):
        url = url.rsplit("/", 1)[0]

    if full_url:
        return url

    alias = str(context.channel_alias)
    if not alias.endswith("/"):
        alias += "/"
    return url.replace(alias, "").replace("https://repo.anaconda.com/", "").rstrip("/")


def installed_packages(
    prefix: Path | str, sorted: bool = True, matching: str | None = None
) -> Iterable[PrefixRecord]:
    import re
    from pathlib import Path

    from rattler import PrefixRecord

    jsons = list(Path(prefix, "conda-meta").glob("*.json"))
    if sorted:
        jsons.sort()
    for path in jsons:
        name, _, _ = path.stem.rsplit("-", 2)
        if matching is None or (matching and re.match(matching, name) is not None):
            yield PrefixRecord.from_path(path)


def dist_str(pkg: PackageRecord) -> str:
    channel_and_subdir = channel_name_or_url(pkg.channel)
    if not channel_and_subdir.endswith(pkg.subdir):
        channel_and_subdir += f"/{pkg.subdir}"
    return f"{channel_and_subdir}::{pkg.name.normalized}-{pkg.version}-{pkg.build}"


def print_exception(exc: Exception, console: Console | None = None) -> None:
    from rich.rule import Rule

    console = console or create_console()
    console.print(
        Rule(title=f"[red][dim]error:[/dim] {type(exc).__name__}", style="red")
    )
    console.print(str(exc).rstrip())
    console.print(Rule(style="red"))
