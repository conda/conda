# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations
from typing import TYPE_CHECKING

from ....auxlib.ish import dals
from ...argparse import ArgumentParser
from ...helpers import (
    add_parser_prefix,
    add_parser_experimental_solver,
    add_output_and_prompt_options,
)

if TYPE_CHECKING:
    from argparse import _SubParsersAction


def configure_parser(
    parent: _SubParsersAction | None = None, name: str = "remove"
) -> ArgumentParser:
    help_ = "Remove an environment"
    description = dals(
        """
        Remove an environment

        Removes a provided environment.  You must deactivate the existing
        environment before you can remove it.
        """
    )
    epilog = dals(
        """
        Examples:

            conda env remove --name FOO
            conda env remove -n FOO
        """
    )

    # when a parent parser is specified add this as a subparser, otherwise create a new parser
    if parent:
        parser = parent.add_parser(name, help=help_, description=description, epilog=epilog)
    else:
        parser = ArgumentParser(name, description=description, epilog=epilog)

    # add options
    add_parser_prefix(parser)
    add_parser_experimental_solver(parser)
    add_output_and_prompt_options(parser)

    # set executable for this scope
    parser.set_defaults(func=".main_remove.execute")

    return parser
