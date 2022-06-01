# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

import os
from argparse import RawDescriptionHelpFormatter

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
    """Validate that we are receiving at least one value for --name or --prefix"""
    common.ensure_name_or_prefix(args, "env rename")
    prefix = args.name if args.name else args.prefix

    return locate_prefix_by_name(prefix)


def validate_destination(dest: str) -> str:
    """Ensure that our destination does not exist"""
    if os.sep in dest:
        dest = expand(dest)
    else:
        dest = validate_prefix_name(dest, ctx=context, allow_base=False)

    if os.path.exists(dest):
        raise CondaEnvException("Environment destination already exists")

    return dest

def execute(args, _):
    """
    Execute the command for renaming an existing environment
    """
    src = validate_src(args)
    dest = validate_destination(args.destination)
    install.clone(src, dest, quiet=context.quiet, json=context.json, use_context=False)
    rm_rf(src)
