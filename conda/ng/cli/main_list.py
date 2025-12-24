"""CLI reimplementation for list"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from argparse import ArgumentParser, Namespace


def execute(args: Namespace, parser: ArgumentParser) -> int:
    from rich.console import Console
    from rich.rule import Rule

    from conda.base.context import context
    from conda.utils import human_bytes

    from .common import channel_name_or_url, create_table
    from .install import installed_packages

    prefix = context.target_prefix
    table = create_table(
        "Name",
        "Version",
        "Build",
        "Channel",
        "Subdir",
        "Size",
        "Requested as",
    )
    requested = 0
    implicit = 0
    size = 0
    for pkg in installed_packages(prefix):
        requested_spec = (
            None if pkg.requested_spec in (None, "None") else str(pkg.requested_spec)
        )
        if requested_spec:
            requested += 1
        else:
            implicit += 1
        pkg_size = sum(path.size_in_bytes or 0 for path in pkg.paths_data.paths)
        size += pkg_size
        table.add_row(
            pkg.name.normalized,
            str(pkg.version),
            pkg.build,
            channel_name_or_url(pkg.channel, args.show_channel_urls),
            pkg.subdir,
            human_bytes(pkg_size),
            requested_spec,
            style=None if requested_spec else "dim",
        )
    table.caption = (
        f"[bold]{requested}[/] requested packages, [bold]{implicit}[/] transitive dependencies. "
        f"[bold]{human_bytes(size)}[/] total size."
    )
    Console().print(Rule(prefix, style=None), "", table)

    return 0
