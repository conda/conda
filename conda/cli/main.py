# (c) Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.
'''conda is a tool for managing environments and packages.

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
'''

from __future__ import print_function, division, absolute_import

import sys
import importlib
from ..exceptions import CommandNotFoundError, CondaRuntimeError, CondaException

def main():
    if len(sys.argv) > 1:
        argv1 = sys.argv[1]
        if argv1 in ('..activate', '..deactivate', '..checkenv', '..changeps1'):
            import conda.cli.activate as activate
            activate.main()
            return
        if argv1 in ('activate', 'deactivate'):

            message = "Error: '%s' is not a conda command.\n" % argv1
            if sys.platform != 'win32':
                message += ' Did you mean "source %s" ?\n' % ' '.join(sys.argv[1:])

            raise CommandNotFoundError(message)

    if len(sys.argv) == 1:
        sys.argv.append('-h')

    import logging
    from conda.cli import conda_argparse
    import argparse
    import conda

    p = conda_argparse.ArgumentParser(
        description='conda is a tool for managing and deploying applications,'
                    ' environments and packages.'
    )
    p.add_argument(
        '-V', '--version',
        action='version',
        version='conda %s' % conda.__version__,
        help="Show the conda version number and exit."
    )
    p.add_argument(
        "--debug",
        action="store_true",
        help="Show debug output."
    )
    p.add_argument(
        "--json",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    sub_parsers = p.add_subparsers(
        metavar='command',
        dest='cmd',
    )
    # http://bugs.python.org/issue9253
    # http://stackoverflow.com/a/18283730/1599393
    sub_parsers.required = True

    main_modules = ["info", "help", "list", "search", "create", "install", "update",
                    "remove", "config", "clean"]
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

    sub_parsers.completer = completer
    args = p.parse_args()

    if getattr(args, 'json', False):
        # Silence logging info to avoid interfering with JSON output
        for logger in logging.Logger.manager.loggerDict:
            if logger not in ('fetch', 'progress'):
                logging.getLogger(logger).setLevel(logging.CRITICAL + 1)

    if args.debug:
        logging.disable(logging.NOTSET)
        logging.basicConfig(level=logging.DEBUG)

    exit_code = args_func(args, p)
    if isinstance(exit_code, int):
        return exit_code


def args_func(args, p):
    from conda.cli import common

    use_json = getattr(args, 'json', False)
    try:
        exit_code = args.func(args, p)
        if isinstance(exit_code, int):
            return exit_code
    except RuntimeError as e:
        raise CondaRuntimeError(e, use_json)
    except Exception as e:
        raise CondaException(e, use_json)


if __name__ == '__main__':
    main()
