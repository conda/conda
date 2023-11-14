# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""CLI implementation for `conda-env list`.

Lists available conda environments.
"""
from argparse import ArgumentParser, _SubParsersAction

from conda.core.envs_manager import list_all_known_prefixes

from . import common


def configure_parser(sub_parsers: _SubParsersAction, **kwargs) -> ArgumentParser:
    from ..auxlib.ish import dals
    from .helpers import add_parser_json

    summary = "List the Conda environments."
    description = summary
    epilog = dals(
        """
        Examples::

            conda env list
            conda env list --json

        """
    )
    p = sub_parsers.add_parser(
        "list",
        help=summary,
        description=description,
        epilog=epilog,
        **kwargs,
    )

    add_parser_json(p)

    p.set_defaults(func="conda.cli.main_env_list.execute")

    return p


def execute(args, parser):
    info_dict = {"envs": list_all_known_prefixes()}
    common.print_envs_list(info_dict["envs"], not args.json)

    if args.json:
        common.stdout_json(info_dict)

    return 0
