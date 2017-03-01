# (c) Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.
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

from __future__ import absolute_import, division, print_function, unicode_literals

import importlib
import sys
from argparse import SUPPRESS
from logging import CRITICAL, DEBUG, getLogger

from .. import __version__

log = getLogger(__name__)


def generate_parser():
    from ..cli import conda_argparse
    p = conda_argparse.ArgumentParser(
        description='conda is a tool for managing and deploying applications,'
                    ' environments and packages.',
    )
    p.add_argument(
        '-V', '--version',
        action='version',
        version='conda %s' % __version__,
        help="Show the conda version number and exit."
    )
    p.add_argument(
        "--debug",
        action="store_true",
        help=SUPPRESS,
    )
    p.add_argument(
        "--json",
        action="store_true",
        help=SUPPRESS,
    )
    sub_parsers = p.add_subparsers(
        metavar='command',
        dest='cmd',
    )
    # http://bugs.python.org/issue9253
    # http://stackoverflow.com/a/18283730/1599393
    sub_parsers.required = True

    return p, sub_parsers


def _main(*args):
    from ..base.constants import SEARCH_PATH
    from ..base.context import context

    from ..gateways.logging import set_all_logger_level, set_verbosity

    if len(args) == 1:
        args = args + ('-h',)

    p, sub_parsers = generate_parser()

    main_modules = ["info", "help", "list", "search", "create", "install", "update",
                    "remove", "config", "clean", "package"]
    modules = ["conda.cli.main_"+suffix for suffix in main_modules]
    for module in modules:
        imported = importlib.import_module(module)
        imported.configure_parser(sub_parsers)
        if "update" in module:
            imported.configure_parser(sub_parsers, name='upgrade')
        if "remove" in module:
            imported.configure_parser(sub_parsers, name='uninstall')

    from conda.cli.find_commands import find_commands

    def completer(prefix, **kwargs):
        return [i for i in list(sub_parsers.choices) + find_commands()
                if i.startswith(prefix)]

    # when using sys.argv, first argument is generally conda or __main__.py.  Ignore it.
    if (any(sname in args[0] for sname in ('conda', 'conda.exe', '__main__.py', 'conda-script.py'))
        and (args[1] in list(sub_parsers.choices.keys()) + find_commands()
             or args[1].startswith('-'))):
        log.debug("Ignoring first argument (%s), as it is not a subcommand", args[0])
        args = args[1:]

    sub_parsers.completer = completer
    args = p.parse_args(args)

    context.__init__(SEARCH_PATH, 'conda', args)

    if getattr(args, 'json', False):
        # Silence logging info to avoid interfering with JSON output
        for logger in ('print', 'dotupdate', 'stdoutlog', 'stderrlog'):
            getLogger(logger).setLevel(CRITICAL + 1)

    if context.debug:
        set_all_logger_level(DEBUG)
    elif context.verbosity:
        set_verbosity(context.verbosity)
        log.debug("verbosity set to %s", context.verbosity)

    exit_code = args.func(args, p)
    if isinstance(exit_code, int):
        return exit_code


def main(*args):
    if not args:
        args = sys.argv

    if not args:
        args = sys.argv

    log.debug("conda.cli.main called with %s", args)
    if len(args) > 1:
        argv1 = args[1].strip()
        if argv1.startswith('..'):
            import conda.cli.activate as activate
            activate.main()
            return
        if argv1 in ('activate', 'deactivate'):

            message = "'%s' is not a conda command.\n" % argv1
            from ..common.compat import on_win
            if not on_win:
                message += ' Did you mean "source %s" ?\n' % ' '.join(args[1:])

            from ..exceptions import CommandNotFoundError
            raise CommandNotFoundError(argv1, message)

    from ..exceptions import conda_exception_handler
    return conda_exception_handler(_main, *args)


if __name__ == '__main__':
    main()
