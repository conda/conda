# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Implementation for `conda plugins update` subcommand."""

from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING

from ....base.context import context
from ....cli import main_update
from ....cli.helpers import (
    add_parser_create_install_update,
    add_parser_frozen_env,
    add_parser_prune,
    add_parser_solver,
    add_parser_update_modifiers,
)
from ....common.constants import NULL
from ....exceptions import CondaValueError
from .package_validation import (
    get_installed_plugin_package_names,
    require_plugin_transaction,
    require_plugin_update_environment,
)

if TYPE_CHECKING:
    from argparse import ArgumentParser, Namespace


HELP = "Update conda plugin packages in an environment."


def configure_parser(parser: ArgumentParser) -> None:
    parser.description = HELP
    add_parser_frozen_env(parser)

    solver_mode_options, _, _ = add_parser_create_install_update(
        parser, include_only_deps=False
    )
    add_parser_prune(solver_mode_options)
    add_parser_solver(solver_mode_options)
    solver_mode_options.add_argument(
        "--force-reinstall",
        action="store_true",
        default=NULL,
        help="Ensure that any requested plugin package is uninstalled and reinstalled, even if it already exists in the environment.",
    )
    add_parser_update_modifiers(
        solver_mode_options,
        include_update_all=False,
    )
    solver_mode_options.add_argument(
        "--update-all",
        "--all",
        action="store_true",
        dest="update_all_plugins",
        default=False,
        help="Update all installed conda plugin packages without updating other packages directly.",
    )
    parser.set_defaults(func=execute, _plugin_parser=parser)


def execute(args: Namespace) -> int:
    if args.update_all_plugins:
        if args.file or args.packages:
            raise CondaValueError(
                "cannot combine --all with plugin package names or --file"
            )

        args.packages = sorted(
            get_installed_plugin_package_names(context.target_prefix)
        )
        if not args.packages:
            raise CondaValueError("No installed conda plugins found to update.")
    else:
        args._validate_environment = require_plugin_update_environment

    args._validate_transaction = partial(
        require_plugin_transaction,
        prefetch_link_precs=True,
        command="update",
    )
    args.cmd = "update"
    with context._override("auto_update_conda", False):
        return main_update.execute(args, args._plugin_parser)
