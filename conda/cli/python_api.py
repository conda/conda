# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import absolute_import, division, print_function, unicode_literals

from logging import getLogger

from .conda_argparse import do_call
from ..common.compat import encode_arguments
from .main import generate_parser
from ..base.constants import SEARCH_PATH
from ..base.context import context
from ..common.io import CaptureTarget, argv, captured
from ..exceptions import conda_exception_handler
from ..gateways.logging import initialize_std_loggers

log = getLogger(__name__)


class Commands:
    CLEAN = "clean"
    CONFIG = "config"
    CREATE = "create"
    INFO = "info"
    INSTALL = "install"
    HELP = "help"
    LIST = "list"
    REMOVE = "remove"
    SEARCH = "search"
    UPDATE = "update"
    RUN = "run"


STRING = CaptureTarget.STRING
STDOUT = CaptureTarget.STDOUT

# Note, a deviated copy of this code appears in tests/test_create.py
def run_command(command, *arguments, **kwargs):
    """Runs a conda command in-process with a given set of command-line interface arguments.

    Differences from the command-line interface:
        Always uses --yes flag, thus does not ask for confirmation.

    Args:
        command: one of the Commands.
        *arguments: instructions you would normally pass to the conda comamnd on the command line
                    see below for examples. Be very careful to delimit arguements exactly as you
                    want them to be delivered. No 'combine then split at spaces' or other
                    information destroying processing gets performed on the arguments.
        **kwargs: special instructions for programmatic overrides

    Keyword Args:
        use_exception_handler: defaults to False. False will let the code calling
          `run_command` handle all exceptions.  True won't raise when an exception
          has occured, and instead give a non-zero return code
        search_path: an optional non-standard search path for configuration information
          that overrides the default SEARCH_PATH
        stdout: Define capture behavior for stream sys.stdout. Defaults to STRING.
          STRING captures as a string.  None leaves stream untouched.
          Otherwise redirect to file-like object stdout.
        stderr: Define capture behavior for stream sys.stderr. Defaults to STRING.
          STRING captures as a string.  None leaves stream untouched.
          STDOUT redirects to stdout target and returns None as stderr value.
          Otherwise redirect to file-like object stderr.

    Returns: a tuple of stdout, stderr, and return_code.
        stdout, stderr are either strings, None or the corresponding file-like function argument.

    Examples:
        >>  run_command(Commands.CREATE, "-n", "newenv", "python=3", "flask",
        use_exception_handler=True)
        >>  run_command(Commands.CREATE, "-n", "newenv", "python=3", "flask")
        >>  run_command(Commands.CREATE, ["-n", "newenv", "python=3", "flask"], search_path=())


    """
    initialize_std_loggers()
    use_exception_handler = kwargs.pop('use_exception_handler', False)
    configuration_search_path = kwargs.pop('search_path', SEARCH_PATH)
    stdout = kwargs.pop('stdout', STRING)
    stderr = kwargs.pop('stderr', STRING)
    p = generate_parser()

    arguments = list(arguments)
    arguments.insert(0, command)

    args = p.parse_args(arguments)
    args.yes = True  # always skip user confirmation, force setting context.always_yes
    context.__init__(
        search_path=configuration_search_path,
        argparse_args=args,
    )

    from subprocess import list2cmdline
    log.debug("executing command >>>  conda %s", list2cmdline(arguments))
    try:
        with argv(['python_api'] + encode_arguments(arguments)), captured(stdout, stderr) as c:
            if use_exception_handler:
                return_code = conda_exception_handler(do_call, args, p)
            else:
                return_code = do_call(args, p)
    except Exception as e:
        log.debug("\n  stdout: %s\n  stderr: %s", c.stdout, c.stderr)
        e.stdout, e.stderr = c.stdout, c.stderr
        raise e
    return_code = return_code or 0
    log.debug("\n  stdout: %s\n  stderr: %s\n  return_code: %s", c.stdout, c.stderr, return_code)
    return c.stdout, c.stderr, return_code
