# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import argparse

from conda.base.context import context
from conda.cli.main import init_loggers
from conda.plugins import CondaSubcommand, hookimpl

from .shell_plugins import PluginActivator


def get_parsed_args(argv: list[str]) -> argparse.Namespace:
    """
    Parse CLI arguments to determine desired command.
    Create namespace with 'command' key, optional 'dev' key and, for activate only,
    optional 'env' and 'stack' keys.
    """
    parser = argparse.ArgumentParser(
        "conda shell",
        description="Process conda activate, deactivate, and reactivate",
    )
    add_subparsers(parser)
    args = parser.parse_args(argv)

    return args


def add_subparsers(parser: argparse.ArgumentParser) -> None:
    """
    Add activate, deactivate and reactivate commands, along with associated sub-commands, to parser
    """
    commands = parser.add_subparsers(
        required=True,
        dest="command",
    )

    activate = commands.add_parser(
        "activate",
        help="Activate a conda environment",
    )
    activate.add_argument(
        "env",
        metavar="env_name_or_prefix",
        default=None,
        type=str,
        nargs="?",
        help="""
            The environment name or prefix to activate. If the prefix is a relative path,
            it must start with './' (or '.\' on Windows). If no environment is specified,
            the base environment will be activated.
            """,
    )
    stack = activate.add_mutually_exclusive_group()
    stack.add_argument(
        "--stack",
        action="store_true",
        help="""
        Stack the environment being activated on top of the
        previous active environment, rather replacing the
        current active environment with a new one. Currently,
        only the PATH environment variable is stacked. This
        may be enabled implicitly by the 'auto_stack'
        configuration variable.
        """,
    )
    stack.add_argument(
        "--no-stack",
        dest="stack",
        action="store_false",
        help="Do not stack the environment. Overrides 'auto_stack' setting.",
    )
    activate.add_argument(
        "--dev", action="store_true", default=False, help=argparse.SUPPRESS
    )

    deactivate = commands.add_parser(
        "deactivate", help="Deactivate the current active conda environment"
    )
    deactivate.add_argument(
        "--dev", action="store_true", default=False, help=argparse.SUPPRESS
    )

    reactivate = commands.add_parser(
        "reactivate",
        help="Reactivate the current conda environment, updating environment variables",
    )
    reactivate.add_argument(
        "--dev", action="store_true", default=False, help=argparse.SUPPRESS
    )


def execute(argv: list[str]) -> SystemExit:
    """
    Run process associated with parsed CLI command (activate, deactivate, reactivate).
    This plugin is intended for use only with POSIX shells.
    """
    args = get_parsed_args(argv)

    context.__init__()
    init_loggers(context)

    activator = PluginActivator()
    cmds_dict = activator.parse_and_build(activator, args)

    return activator.activate(cmds_dict)


@hookimpl
def conda_subcommands():
    yield CondaSubcommand(
        name="shell",
        summary="Plugin for POSIX shells used for activate, deactivate, and reactivate",
        action=execute,
    )
