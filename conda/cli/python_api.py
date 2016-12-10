# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from importlib import import_module
from logging import getLogger
from shlex import split

from ..base.context import context, reset_context
from ..cli.main import generate_parser
from ..common.compat import on_win
from ..common.io import captured, replace_log_streams
from ..exceptions import conda_exception_handler

log = getLogger(__name__)


class Commands:
    CONFIG = "config"
    CLEAN = "clean"
    CREATE = "create"
    INFO = "info"
    INSTALL = "install"
    LIST = "list"
    REMOVE = "remove"
    SEARCH = "search"
    UPDATE = "update"


def get_configure_parser_function(command):
    module = 'conda.cli.main_' + command
    return import_module(module).configure_parser


def escape_for_winpath(p):
    return p.replace('\\', '\\\\') if on_win else p


def run_command(command, *arguments, **kwargs):
    """

    Args:
        command: one of the Commands.X
        *arguments: instructions you would normally pass to the conda comamnd on the command line
                    see below for examples
        **kwargs: special instructions for programmatic overrides
          - use_exception_handler: defaults to False.  False will let the code calling
              `run_command` handle all exceptions.  True won't raise when an exception
              has occured, and instead give a non-zero return code
                  currently only `use_exception_handler`, which defaults to False

    Returns: a tuple of stdout, stderr, and return_code

    Examples:
        >>  run_command(Commands.CREATE, "-n newenv python=3 flask")
        >>  run_command(Commands.CREATE, "-n newenv", "python=3", "flask")
        >>  run_command(Commands.CREATE, ["-n newenv", "python=3", "flask"])


    """
    use_exception_handler = kwargs.get('use_exception_handler', False)
    p, sub_parsers = generate_parser()
    get_configure_parser_function(command)(sub_parsers)

    arguments = map(escape_for_winpath, arguments)
    command_line = "%s %s" % (command, " ".join(arguments))
    split_command_line = split(command_line)

    args = p.parse_args(split_command_line)
    context._add_argparse_args(args)
    log.debug("executing command >>> %s", command_line)
    with captured() as c, replace_log_streams():
        if use_exception_handler:
            return_code = conda_exception_handler(args.func, args, p)
        else:
            return_code = args.func(args, p)
    log.debug("\n  stdout: %s\n  stderr: %s\n  return_code: %s", c.stdout, c.stderr, return_code)
    if command == Commands.CONFIG:
        reset_context()
    return c.stdout, c.stderr, return_code
