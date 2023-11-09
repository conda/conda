# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""CLI implementation for `conda-env config`.

Allows for programmatically interacting with conda-env's configuration files (e.g., `~/.condarc`).
"""
from argparse import RawDescriptionHelpFormatter

from .main_env_vars import configure_parser as configure_vars_parser


def configure_parser(sub_parsers):
    from ..auxlib.ish import dals

    summary = "Configure a conda environment."
    description = summary
    epilog = dals(
        """
        Examples::

            conda env config vars list
            conda env config --append channels conda-forge

        """
    )

    config_parser = sub_parsers.add_parser(
        "config",
        formatter_class=RawDescriptionHelpFormatter,
        help=summary,
        description=description,
        epilog=epilog,
    )
    config_parser.set_defaults(func=".main_config.execute")
    config_subparser = config_parser.add_subparsers()
    configure_vars_parser(config_subparser)


def execute(args, parser):
    parser.parse_args(["config", "--help"])
