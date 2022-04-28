# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from argparse import RawDescriptionHelpFormatter

from conda.cli import conda_argparse as ca

DESCRIPTION = """
Renames an environment based
"""

EXAMPLE = """
examples:
    conda env rename -n test123 test321
    conda env rename --name test123 test321
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
    ca.add_parser_prefix(p)

    p.add_argument("destination", nargs=1, help="New name for the conda environment")
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


def execute(args, parser):
    print(parser.destination)
    print("hai")
