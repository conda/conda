# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Implementation for `conda plugins install` subcommand."""

from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING

from ....cli import main_install
from ....cli.helpers import (
    add_parser_create_install_update,
    add_parser_frozen_env,
    add_parser_prune,
    add_parser_solver,
    add_parser_update_modifiers,
)
from ....common.constants import NULL
from .package_validation import (
    require_explicit_plugin_packages,
    require_plugin_install_transaction,
)

if TYPE_CHECKING:
    from argparse import ArgumentParser, Namespace


HELP = "Install conda plugin packages into an environment."


def configure_parser(parser: ArgumentParser) -> None:
    parser.description = HELP
    add_parser_frozen_env(parser)

    solver_mode_options, _, _ = add_parser_create_install_update(parser)
    add_parser_prune(solver_mode_options)
    add_parser_solver(solver_mode_options)
    solver_mode_options.add_argument(
        "--force-reinstall",
        action="store_true",
        default=NULL,
        help="Ensure that any requested plugin package is uninstalled and reinstalled, even if it already exists in the environment.",
    )
    add_parser_update_modifiers(solver_mode_options, include_update_all=False)
    parser.set_defaults(func=execute, _plugin_parser=parser, revision=None)


def execute(args: Namespace) -> int:
    args._validate_explicit_packages = require_explicit_plugin_packages
    args._validate_transaction = require_plugin_install_transaction
    args._validate_prepared_transaction = partial(
        require_plugin_install_transaction,
        inspect_link_precs=True,
    )
    args.cmd = "install"
    return main_install.execute(args, args._plugin_parser)
