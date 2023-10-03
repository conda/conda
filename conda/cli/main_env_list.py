# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""CLI implementation for `conda-env list`.

Lists available conda environments.
"""
from argparse import RawDescriptionHelpFormatter

from conda.cli import common
from conda.cli.conda_argparse import add_parser_json
from conda.core.envs_manager import list_all_known_prefixes

description = """
List the Conda environments
"""

example = """
examples:
    conda env list
    conda env list --json
"""


def configure_parser(sub_parsers):
    list_parser = sub_parsers.add_parser(
        "list",
        formatter_class=RawDescriptionHelpFormatter,
        description=description,
        help=description,
        epilog=example,
    )

    add_parser_json(list_parser)

    list_parser.set_defaults(func=".main_list.execute")


def execute(args, parser):
    info_dict = {"envs": list_all_known_prefixes()}
    common.print_envs_list(info_dict["envs"], not args.json)

    if args.json:
        common.stdout_json(info_dict)
