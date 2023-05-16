# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""conda is a tool for managing environments and packages.

conda provides the following commands:

    Information
    ===========

    info       : display information about the current install
    list       : list packages linked into a specified environment
    search     : print information about a specified package
    help       : display a list of available conda commands and their help
                 strings

    Package Management
    ==================

    create     : create a new conda environment from a list of specified
                 packages
    install    : install new packages into an existing conda environment
    update     : update packages in a specified conda environment


    Packaging
    =========

    package    : create a conda package in an environment

Additional help for each command can be accessed by using:

    conda <command> -h
"""
import sys


def init_loggers(context=None):
    from logging import CRITICAL, getLogger

    from ..gateways.logging import initialize_logging, set_verbosity

    initialize_logging()
    if context and context.json:
        # Silence logging info to avoid interfering with JSON output
        for logger in ("conda.stdout.verbose", "conda.stdoutlog", "conda.stderrlog"):
            getLogger(logger).setLevel(CRITICAL + 1)

    if context:
        if context.verbosity:
            set_verbosity(context.verbosity)


def generate_parser(*args, **kwargs):
    """
    Some code paths import this function directly from this module instead
    of from conda_argparse. We add the forwarder for backwards compatibility.
    """
    from .conda_argparse import generate_parser

    return generate_parser(*args, **kwargs)


def main_subshell(*args, post_parse_hook=None, **kwargs):
    """Entrypoint for the "subshell" invocation of CLI interface. E.g. `conda create`."""
    # defer import here so it doesn't hit the 'conda shell.*' subcommands paths
    from .conda_argparse import generate_parser

    args = args or ["--help"]

    p = generate_parser()
    args = p.parse_args(args)

    from ..base.context import context

    context.__init__(argparse_args=args)
    init_loggers(context)

    # used with main_pip.py
    if post_parse_hook:
        post_parse_hook(args, p)

    from .conda_argparse import do_call

    exit_code = do_call(args, p)
    if isinstance(exit_code, int):
        return exit_code
    elif hasattr(exit_code, "rc"):
        return exit_code.rc


def main_sourced(shell, *args, **kwargs):
    """Entrypoint for the "sourced" invocation of CLI interface. E.g. `conda activate`."""
    shell = shell.replace("shell.", "", 1)

    # This is called any way later in conda.activate, so no point in removing it
    from ..base.context import context

    context.__init__()
    init_loggers(context)

    from ..activate import _build_activator_cls

    try:
        activator_cls = _build_activator_cls(shell)
    except KeyError:
        from ..exceptions import CondaError

        raise CondaError("%s is not a supported shell." % shell)

    activator = activator_cls(args)
    print(activator.execute(), end="")
    return 0


def main(*args, **kwargs):
    # conda.common.compat contains only stdlib imports
    from ..common.compat import ensure_text_type
    from ..exception_handler import conda_exception_handler

    # cleanup argv
    args = args or sys.argv[1:]  # drop executable/script
    args = tuple(ensure_text_type(s) for s in args)

    if args and args[0].strip().startswith("shell."):
        main = main_sourced
    else:
        main = main_subshell

    return conda_exception_handler(main, *args, **kwargs)
