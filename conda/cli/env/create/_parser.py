# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from __future__ import annotations
from typing import TYPE_CHECKING

from ....auxlib.ish import dals
from ...helpers import (
    add_parser_prefix,
    add_parser_networking,
    add_parser_default_packages,
    add_parser_json,
    add_parser_experimental_solver,
)

if TYPE_CHECKING:
    from argparse import _SubParsersAction


def configure_parser(
    parent: _SubParsersAction | None = None, name: str = "create"
) -> ArgumentParser:
    help_ = "Create an environment based on an environment definition file."
    description = dals(
        """
        Create an environment based on an environment definition file.

        If using an environment.yml file (the default), you can name the
        environment in the first line of the file with 'name: envname' or
        you can specify the environment name in the CLI command using the
        -n/--name argument. The name specified in the CLI will override
        the name specified in the environment.yml file.

        Unless you are in the directory containing the environment definition
        file, use -f to specify the file path of the environment definition
        file you want to use.
        """
    )
    epilog = dals(
        """
        examples:
            conda env create
            conda env create -n envname
            conda env create folder/envname
            conda env create -f /path/to/environment.yml
            conda env create -f /path/to/requirements.txt -n envname
            conda env create -f /path/to/requirements.txt -p /home/user/envname
        """
    )

    # when a parent parser is specified add this as a subparser, otherwise create a new parser
    if parent:
        parser = parent.add_parser(name, help=help_, description=description, epilog=epilog)
    else:
        parser = ArgumentParser(name, description=description, epilog=epilog)

    # add options
    parser.add_argument(
        "-f",
        "--file",
        action="store",
        help="Environment definition file (default: environment.yml)",
        default="environment.yml",
    )
    add_parser_prefix(parser)
    add_parser_networking(parser)
    parser.add_argument(
        "remote_definition",
        help="Remote environment definition / IPython notebook",
        action="store",
        default=None,
        nargs="?",
    )
    parser.add_argument(
        "--force",
        help=(
            "Force creation of environment (removing a previously-existing "
            "environment of the same name)."
        ),
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "-d",
        "--dry-run",
        help="Only display what can be done with the current command, arguments, "
        "and other flags. Remove this flag to actually run the command.",
        action="store_true",
        default=False,
    )
    add_parser_default_packages(parser)
    add_parser_json(parser)
    add_parser_experimental_solver(parser)

    # set executable for this scope
    parser.set_defaults(func="conda.cli.env.create.__main__.execute")

    return parser
