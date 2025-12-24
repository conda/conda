"""
Common utilities for the CLI layer.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Literal

    from rattler import GenericVirtualPackage
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
