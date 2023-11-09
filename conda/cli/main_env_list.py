# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""CLI implementation for `conda-env list`.

Lists available conda environments.
"""
from argparse import RawDescriptionHelpFormatter

from conda.cli import common
from conda.cli.conda_argparse import add_parser_json
from conda.core.envs_manager import list_all_known_prefixes


def configure_parser(sub_parsers):
    from ..auxlib.ish import dals

    summary = "List the Conda environments."
    description = summary
    epilog = dals(
        """
        Examples::

            conda env list
            conda env list --json

        """
    )
    list_parser = sub_parsers.add_parser(
        "list",
        formatter_class=RawDescriptionHelpFormatter,
        help=summary,
        description=description,
        epilog=epilog,
    )

    add_parser_json(list_parser)

    list_parser.set_defaults(func=".main_list.execute")


def execute(args, parser):
    info_dict = {"envs": list_all_known_prefixes()}
    common.print_envs_list(info_dict["envs"], not args.json)

    if args.json:
        common.stdout_json(info_dict)
    return 0
