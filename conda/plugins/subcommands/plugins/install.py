# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Implementation for `conda plugins install` subcommand."""

from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING

from ....base.constants import DEFAULT_JSON_REPORTER_BACKEND
from ....base.context import context
from ....cli import main_install
from ....cli.helpers import (
    add_parser_create_install_update,
    add_parser_frozen_env,
    add_parser_prune,
    add_parser_solver,
    add_parser_update_modifiers,
)
from ....common.constants import NULL
from ....common.terminal import is_interactive_tty
from ....core.prefix_data import PrefixData
from ....reporters import prompt
from .package_validation import (
    require_conda_packages_only,
    require_explicit_plugin_packages,
    require_plugin_transaction,
)

if TYPE_CHECKING:
    from argparse import ArgumentParser, Namespace

    from ....exceptions import EnvironmentIsFrozenError


HELP = "Install conda plugin packages into an environment."


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
    add_parser_update_modifiers(solver_mode_options, include_update_all=False)
    parser.set_defaults(func=execute, _plugin_parser=parser, revision=None)


def _confirm_frozen(error: EnvironmentIsFrozenError) -> bool:
    if (
        context.always_yes
        or context.dry_run
        or context.console == DEFAULT_JSON_REPORTER_BACKEND
        or not is_interactive_tty()
    ):
        return False
    try:
        choice = prompt(
            f"{error}\n\nOverride the freeze for this plugin installation",
            choices=("yes", "no"),
            default="no",
        )
    except KeyboardInterrupt:
        return False
    return choice == "yes"


def execute(args: Namespace) -> int:
    args._validate_explicit_packages = require_explicit_plugin_packages
    args._validate_transaction = partial(
        require_plugin_transaction,
        prefetch_link_precs=True,
    )
    args.cmd = "install"
    prefix_data = PrefixData.from_context()
    if (
        context.protect_frozen_envs
        and prefix_data.is_base()
        and prefix_data.is_frozen()
    ):
        args._confirm_frozen = _confirm_frozen
        args._validate_environment = partial(
            require_conda_packages_only, command="install"
        )
        with context._override("auto_update_conda", False):
            return main_install.execute(args, args._plugin_parser)
    return main_install.execute(args, args._plugin_parser)
