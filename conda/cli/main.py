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

def main():
    if len(sys.argv) > 1:
        argv1 = sys.argv[1]
        if argv1 in ('..activate', '..deactivate', '..checkenv', '..setps1'):
            import conda.cli.activate as activate
            activate.main()
            return
        if argv1 in ('activate', 'deactivate'):
            sys.stderr.write("Error: '%s' is not a conda command.\n" % argv1)
            if sys.platform != 'win32':
                sys.stderr.write('Did you mean "source %s" ?\n' %
                                 ' '.join(sys.argv[1:]))
            sys.exit(1)

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

    main_modules = ["info", "help", "list", "search", "create", "install", "update",
                    "remove", "config", "init", "clean", "package", "bundle"]
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

    args_func(args, p)

def args_func(args, p):
    from conda.cli import common

    use_json = getattr(args, 'json', False)
    try:
        args.func(args, p)
    except RuntimeError as e:
        if 'maximum recursion depth exceeded' in str(e):
            print_issue_message(e, use_json=use_json)
            raise
        common.error_and_exit(str(e), json=use_json)
    except Exception as e:
        print_issue_message(e, use_json=use_json)
        raise  # as if we did not catch it

def print_issue_message(e, use_json=False):
    from conda.cli import common
    message = ""
    if e.__class__.__name__ not in ('ScannerError', 'ParserError'):
        message = """\
An unexpected error has occurred, please consider sending the
following traceback to the conda GitHub issue tracker at:

    https://github.com/conda/conda/issues

Include the output of the command 'conda info' in your report.

"""
    if use_json:
        import traceback
        common.error_and_exit(message + traceback.format_exc(),
                              error_type="UnexpectedError", json=True)
    print(message)

if __name__ == '__main__':
    main()
