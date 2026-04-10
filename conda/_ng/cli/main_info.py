# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""CLI reimplementation for info"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from argparse import ArgumentParser, Namespace


def execute(args: Namespace, parser: ArgumentParser) -> int:
    from textwrap import dedent

    from rich import box
    from rich.table import Column

    from conda.cli.main_info import get_info_dict, get_main_info_display

    from .common import create_console, create_table

    table = create_table(
        Column(justify="right", style="dim"),
        Column(justify="left"),
        show_header=False,
        show_footer=False,
        box=box.MINIMAL,
    )
    for field, value in get_main_info_display(get_info_dict()).items():
        # HACK get_main_info_display force-"flattens" its multiline values; undo here
        value = dedent((26 * " ") + str(value))
        table.add_row(field, value if value != "None" else "[dim]none[/]")
    create_console().print("", table, "")
