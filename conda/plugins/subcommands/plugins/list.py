# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Implementation for `conda plugins list` subcommand."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ....base.context import context
from ....cli.helpers import add_parser_json
from ....common.serialize import json

if TYPE_CHECKING:
    from argparse import ArgumentParser, Namespace


HELP = "List installed conda plugins."


def configure_parser(parser: ArgumentParser) -> None:
    parser.description = HELP
    add_parser_json(parser)
    parser.set_defaults(func=execute)


def execute(args: Namespace) -> int:
    plugins = context.plugin_manager.get_installed_plugins()

    if context.json:
        print(json.dumps(plugins, indent=2))
        return 0

    if not plugins:
        print("No plugins installed.")
        return 0

    name_width = max(len(plugin["name"]) for plugin in plugins)
    version_width = max(len(plugin["version"]) for plugin in plugins)
    status_width = max(len(plugin["status"]) for plugin in plugins)

    header = (
        f"{'Name':<{name_width}}  "
        f"{'Version':<{version_width}}  "
        f"{'Status':<{status_width}}  "
        "Hooks"
    )
    print(header)
    print("-" * len(header))

    for plugin in plugins:
        print(
            f"{plugin['name']:<{name_width}}  "
            f"{plugin['version']:<{version_width}}  "
            f"{plugin['status']:<{status_width}}  "
            f"{', '.join(plugin['hooks'])}"
        )

    return 0
