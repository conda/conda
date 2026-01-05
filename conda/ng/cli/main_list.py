# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""CLI reimplementation for list"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from argparse import ArgumentParser, Namespace


def execute(args: Namespace, parser: ArgumentParser) -> int:
    from rich.markup import escape
    from rich.rule import Rule

    from conda import __version__
    from conda.base.constants import CONDA_LIST_FIELDS, DEFAULT_CONDA_LIST_FIELDS
    from conda.base.context import context
    from conda.exceptions import ArgumentError
    from conda.utils import human_bytes

    from .common import (
        channel_name_or_url,
        create_console,
        create_table,
        dist_str,
        installed_packages,
    )

    prefix = context.target_prefix
    regex = f"^{args.regex}$" if args.regex and args.full_name else args.regex

    if args.explicit or args.export or args.canonical:
        print("# This file may be used to create an environment using:")
        print("# $ conda.ng create --name <env> --file <this file>")
        print(f"# platform: {context.subdir}")
        print(f"# created-by: conda.ng {__version__}")
        if args.explicit:
            print("@EXPLICIT")
        for pkg in installed_packages(prefix, matching=regex):
            if args.explicit:
                line = pkg.url
                if args.sha256:
                    line += f"#{pkg.sha256.hex()}"
                elif args.md5:
                    line += f"#{pkg.md5.hex()}"
            elif args.export:
                line = f"{pkg.name.normalized}={pkg.version}={pkg.build}"
            else:  # canonical
                line = dist_str(pkg)
            print(line)
        return 0

    fields = args.list_fields or (*DEFAULT_CONDA_LIST_FIELDS, "size", "requested_spec")

    if invalid_fields := set(fields).difference(CONDA_LIST_FIELDS):
        raise ArgumentError(
            f"Invalid fields passed: {sorted(invalid_fields)}. "
            f"Valid options are {list(CONDA_LIST_FIELDS)}."
        )
    table = create_table(*[CONDA_LIST_FIELDS[field] for field in fields])
    requested = 0
    implicit = 0
    size = 0
    for pkg in (
        reversed(installed_packages(prefix, matching=regex))
        if args.reverse
        else installed_packages(prefix, matching=regex)
    ):
        requested_spec = (
            None if pkg.requested_spec in (None, "None") else str(pkg.requested_spec)
        )
        requested_spec = (
            requested_spec or " & ".join(map(str, pkg.requested_specs)) or None
        )
        pkg_size = sum(path.size_in_bytes or 0 for path in pkg.paths_data.paths)
        size += pkg_size
        if requested_spec:
            requested += 1
        else:
            implicit += 1
        row_fields = []
        for field in fields:
            if field == "size":
                row_fields.append(human_bytes(pkg_size))
            elif field == "name":
                row_fields.append(pkg.name.normalized)
            elif field == "channel_name":
                row_fields.append(
                    channel_name_or_url(pkg.channel, args.show_channel_urls)
                )
            elif field == "requested_spec":
                row_fields.append(requested_spec)
            elif field == "dist_str":
                row_fields.append(dist_str(pkg))
            else:
                value = getattr(pkg, field, "N/A")
                row_fields.append(escape(str(value)) if value else None)
        table.add_row(
            *row_fields,
            style=None if requested_spec else "dim",
        )
    table.caption = (
        (f"Query '{regex}' matched " if regex else "Environment has ")
        + f"{requested + implicit} packages: {requested} requested (highlighted), "
        f"{implicit} transitive (dimmed). {human_bytes(size)} total size."
    )
    create_console().print(Rule(prefix, style=None), "", table)

    return 0
