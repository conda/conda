# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""CLI implementation for `conda run`.

Runs the provided command within the specified environment.
"""

import os
import sys
from argparse import REMAINDER, ArgumentParser, Namespace, _SubParsersAction
from logging import getLogger


def configure_parser(sub_parsers: _SubParsersAction, **kwargs) -> ArgumentParser:
    from ..auxlib.ish import dals
    from ..common.constants import NULL
    from .actions import NullCountAction
    from .helpers import add_parser_prefix, add_parser_verbose

    summary = "Run an executable in a conda environment."
    description = summary
    epilog = dals(
        """
        Example::

        $ conda create -y -n my-python-env python=3
        $ conda run -n my-python-env python --version

        Use '--' to separate `conda run`'s options from the executable's options::

        $ conda run -n my-python-env -- python -v
        $ conda run -v -n my-python-env -- tar -tvf file.tar
        """
    )

    p = sub_parsers.add_parser(
        "run",
        help=summary,
        description=description,
        epilog=epilog,
        **kwargs,
    )

    add_parser_prefix(p)
    add_parser_verbose(p)

    p.add_argument(
        "--dev",
        action=NullCountAction,
        help="Sets `CONDA_EXE` to `python -m conda`, assuming the current "
        "working directory contains the root of conda development sources. "
        "This is mainly for use during tests where we test new conda sources "
        "against old Python versions.",
        dest="dev",
        default=NULL,
    )

    p.add_argument(
        "--debug-wrapper-scripts",
        action=NullCountAction,
        help="When this is set, where implemented, the shell wrapper scripts"
        "will use the echo command to print debugging information to "
        "stderr (standard error).",
        dest="debug_wrapper_scripts",
        default=NULL,
    )
    p.add_argument(
        "--cwd",
        help="Current working directory for command to run in. Defaults to "
        "the user's current working directory if no directory is specified.",
        default=os.getcwd(),
    )
    p.add_argument(
        "-s",
        "--no-capture-output",
        "--live-stream",
        action="store_true",
        help="Don't capture stdout/stderr (standard out/standard error).",
        default=False,
    )

    p.add_argument(
        "executable_call",
        nargs=REMAINDER,
        help="Executable name, with additional arguments to be passed to the executable "
        "on invocation. Use '--' to separate conda options from executable options.",
    )

    p.set_defaults(func="conda.cli.main_run.execute")

    return p


def execute(args: Namespace, parser: ArgumentParser) -> int:
    from ..base.context import context
    from ..common.compat import encode_environment
    from ..core.prefix_data import PrefixData
    from ..exceptions import ArgumentError
    from ..gateways.disk.delete import rm_rf
    from ..gateways.subprocess import subprocess_call
    from ..utils import wrap_subprocess_call

    prefix_data = PrefixData.from_context()
    prefix_data.assert_environment()

    # Used to separate subcommand from 'conda run' options
    # e.g. conda run -v -- tar -tvf file.tar
    if args.executable_call and args.executable_call[0] == "--":
        args.executable_call = args.executable_call[1:]

    if not args.executable_call:
        raise ArgumentError("No command specified. Please provide a command to run.")

    # create run script
    script, command = wrap_subprocess_call(
        context.root_prefix,
        str(prefix_data.prefix_path),
        args.dev,
        args.debug_wrapper_scripts,
        args.executable_call,
    )

    # run script
    response = subprocess_call(
        command,
        env=encode_environment(os.environ.copy()),
        path=args.cwd,
        raise_on_error=False,
        capture_output=not args.no_capture_output,
    )

    # display stdout/stderr if it was captured
    if not args.no_capture_output:
        if response.stdout:
            print(response.stdout, file=sys.stdout, end="")
        if response.stderr:
            print(response.stderr, file=sys.stderr, end="")

    # log error
    if response.rc != 0:
        log = getLogger(__name__)
        log.error(
            f"`conda run {' '.join(args.executable_call)}` failed. (See above for error)"
        )

    # remove script
    if "CONDA_TEST_SAVE_TEMPS" not in os.environ:
        rm_rf(script)
    else:
        log = getLogger(__name__)
        log.warning(f"CONDA_TEST_SAVE_TEMPS :: retaining main_run script {script}")

    return response.rc
