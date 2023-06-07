# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import argparse
import sys

from conda.base.context import context
from conda.cli.main import init_loggers
from conda.exceptions import conda_exception_handler
from conda.plugins import CondaShellPlugins, CondaSubcommand, hookimpl

from .common import PosixPluginActivator, add_subparsers


def get_parsed_args(argv: list[str]) -> argparse.Namespace:
    """
    Parse CLI arguments to determine desired command.
    Create namespace with 'command' and 'env' keys.
    """
    parser = argparse.ArgumentParser(
        "posix_plugin_current_logic",
        description="Process conda activate, deactivate, and reactivate",
    )

    add_subparsers(parser)

    try:
        args = parser.parse_args(argv)
    except SystemExit:
        # SystemExit: help blurb was printed, intercepting SystemExit(0) to avoid
        # evaluation of help strings by shell interface
        raise SystemExit(1)

    return args


def handle_env(*args, **kwargs):
    """
    Execute logic associated with parsed CLI command (activate, deactivate, reactivate).
    Print relevant shell commands to stdout, for evaluation by shell forwarding function on return.
    See modified forwarding function at conda/shell/etc/profile.d/conda.sh
    In a final version, this method would either require automatic evaluation logic to be
    run via the user's shell profile or the user would have to manually run the evaluation logic.

    This plugin is intended for use only with POSIX shells.
    """
    args = get_parsed_args(sys.argv[2:])  # drop executable/script and plugin name

    context.__init__()
    init_loggers(context)

    activator = PosixPluginActivator(args)
    print(activator.execute(), end="")

    return 0


def handle_exceptions(*args, **kwargs):
    """
    Upon return, exit the Python interpreter and return the appropriate
    error code if an exception occurs.
    These are handled through main.py and __main__.py during the current
    activate/reactivate/deactivate process.
    """
    return sys.exit(conda_exception_handler(handle_env, *args, **kwargs))


@hookimpl
def conda_subcommands():
    yield CondaSubcommand(
        name="posix_plugin_current_logic",
        summary="Plugin for POSIX shells: handles conda activate, deactivate, and reactivate",
        action=handle_exceptions,
    )


@hookimpl
def conda_shell_plugins():
    yield CondaShellPlugins(
        name="posix_plugin_current_logic",
        summary="Plugin for POSIX shells: handles conda activate, deactivate, and reactivate",
        activator=PosixPluginActivator,
    )
