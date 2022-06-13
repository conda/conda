# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import os
from argparse import RawDescriptionHelpFormatter
from typing import Callable

from conda.base.context import context, locate_prefix_by_name, validate_prefix_name
from conda.cli import common, conda_argparse as c_arg, install
from conda.common.path import expand
from conda.exceptions import CondaEnvException
from conda.gateways.disk.delete import rm_rf

DESCRIPTION = """
Renames an existing environment
"""

EXAMPLE = """
examples:
    conda env rename -n test123 test321
    conda env rename --name test123 test321
    conda env rename -p path/to/test123 test321
    conda env rename --prefix path/to/test123 test321
"""

DRY_RUN_PREFIX = "Dry run action:"


def configure_parser(sub_parsers) -> None:
    p = sub_parsers.add_parser(
        "rename",
        formatter_class=RawDescriptionHelpFormatter,
        description=DESCRIPTION,
        help=DESCRIPTION,
        epilog=EXAMPLE,
    )
    # Add name and prefix args
    c_arg.add_parser_prefix(p)

    p.add_argument("destination", help="New name for the conda environment")
    p.add_argument(
        "--force",
        help=(
            "force creation of environment (removing a previously existing "
            "environment of the same name)."
        ),
        action="store_true",
        default=False,
    )
    p.add_argument(
        "-d",
        "--dry-run",
        help="Only display what would have been done.",
        action="store_true",
        default=False,
    )
    p.set_defaults(func=".main_rename.execute")


def validate_src(args) -> str:
    """
    Validate that we are receiving at least one value for --name or --prefix
    and ensure that the "base" environment is not being renamed
    """
    common.ensure_name_or_prefix(args, "env rename")

    if context.target_prefix == context.root_prefix:
        raise CondaEnvException("The 'base' environment cannot be renamed")

    prefix = args.name if args.name else args.prefix

    if common.is_active_prefix(prefix):
        raise CondaEnvException("Cannot rename the active environment")

    return locate_prefix_by_name(prefix)


def validate_destination(dest: str, force: bool = False) -> str:
    """Ensure that our destination does not exist"""
    if os.sep in dest:
        dest = expand(dest)
    else:
        dest = validate_prefix_name(dest, ctx=context, allow_base=False)

    if not force and os.path.exists(dest):
        raise CondaEnvException("Environment destination already exists")

    return dest


Args = tuple
Kwargs = dict


def execute(args, _):
    """
    Executes the command for renaming an existing environment
    """
    src = validate_src(args)
    dest = validate_destination(args.destination, force=args.force)

    actions: list[tuple[Callable, Args, Kwargs]] = []

    if args.force:
        actions.append((rm_rf, (dest,), {}))

    actions.append(
        (
            install.clone,
            (src, dest),
            {"quiet": context.quiet, "json": context.json, "use_context": False},
        )
    )
    actions.append((rm_rf, (src,), {}))

    for act_func, act_args, act_kwargs in actions:
        if args.dry_run:
            pos_args = ", ".join(act_args)
            print(f"{DRY_RUN_PREFIX} {act_func.__name__} {pos_args}")
        else:
            act_func(*act_args, **act_kwargs)
