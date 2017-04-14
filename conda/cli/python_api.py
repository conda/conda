# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from importlib import import_module
from logging import getLogger
from shlex import split

from ..base.constants import APP_NAME, SEARCH_PATH
from ..base.context import context
from ..cli.main import generate_parser
from ..common.io import captured, replace_log_streams
from ..common.path import win_path_double_escape
from ..exceptions import conda_exception_handler
from ..gateways import initialize_logging

initialize_logging()
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


def run_command(command, *arguments, **kwargs):
    """

    Args:
        command: one of the Commands.X
        *arguments: instructions you would normally pass to the conda command on the command line
                    see below for examples
        **kwargs: special instructions for programmatic overrides
          use_exception_handler: defaults to False.  False will let the code calling
              `run_command` handle all exceptions.  True won't raise when an exception
              has occurred, and instead give a non-zero return code
          search_path: an optional non-standard search path for configuration information
              that overrides the default SEARCH_PATH

    Returns: a tuple of stdout, stderr, and return_code

    Examples:
        >>  run_command(Commands.CREATE, "-n newenv python=3 flask", use_exception_handler=True)
        >>  run_command(Commands.CREATE, "-n newenv", "python=3", "flask")
        >>  run_command(Commands.CREATE, ["-n newenv", "python=3", "flask"], search_path=())


    """
    use_exception_handler = kwargs.get('use_exception_handler', False)
    configuration_search_path = kwargs.get('search_path', SEARCH_PATH)
    p, sub_parsers = generate_parser()
    get_configure_parser_function(command)(sub_parsers)

    arguments = map(win_path_double_escape, arguments)
    command_line = "%s %s" % (command, " ".join(arguments))
    split_command_line = split(command_line)

    args = p.parse_args(split_command_line)
    context.__init__(
        search_path=configuration_search_path,
        app_name=APP_NAME,
        argparse_args=args,
    )
    log.debug("executing command >>>  conda %s", command_line)
    try:
        with captured() as c, replace_log_streams():
            if use_exception_handler:
                return_code = conda_exception_handler(args.func, args, p)
            else:
                return_code = args.func(args, p)
    except Exception as e:
        log.debug("\n  stdout: %s\n  stderr: %s", c.stdout, c.stderr)
        e.stdout, e.stderr = c.stdout, c.stderr
        raise e
    log.debug("\n  stdout: %s\n  stderr: %s\n  return_code: %s", c.stdout, c.stderr, return_code)
    return c.stdout, c.stderr, return_code
