# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Implementation for `conda plugins info` subcommand."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ....base.context import context
from ....cli.helpers import add_parser_json
from ....common.serialize import json

if TYPE_CHECKING:
    from argparse import ArgumentParser, Namespace


HELP = "Show detailed information about an installed conda plugin."


def configure_parser(parser: ArgumentParser) -> None:
    parser.description = HELP
    parser.add_argument(
        "name",
        metavar="NAME",
        help="Installed plugin distribution name or canonical plugin name.",
    )
    add_parser_json(parser)
    parser.set_defaults(func=execute)


def execute(args: Namespace) -> int:
    plugin = context.plugin_manager.get_installed_plugin_info(args.name)

    if context.json:
        print(json.dumps(plugin, indent=2))
        return 0

    fields = (
        ("Name", plugin["name"]),
        ("Version", plugin["version"]),
        ("Status", plugin["status"]),
        ("Canonical name", plugin["canonical_name"]),
        ("Hooks", ", ".join(plugin["hooks"]) or "None"),
        ("Summary", plugin["summary"]),
        ("License", plugin["license"]),
        ("Homepage", plugin["homepage"]),
    )
    label_width = max(len(label) for label, _value in fields)
    for label, value in fields:
        print(f"{label:<{label_width}}: {value}")

    return 0
