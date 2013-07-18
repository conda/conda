# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
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

    build      : build a package from recipe
    package    : create a conda package in an environment
    pip        : call pip and create a conda package in an environment
    index      : updates repodata.json in channel directories

Additional help for each command can be accessed by using:

    conda <command> -h
'''

from __future__ import print_function, division, absolute_import

import sys
import argparse

from conda.cli import conda_argparse
from conda.cli import main_build
from conda.cli import main_clone
from conda.cli import main_create
from conda.cli import main_help
from conda.cli import main_index
from conda.cli import main_info
from conda.cli import main_install
from conda.cli import main_list
from conda.cli import main_remove
from conda.cli import main_package
from conda.cli import main_pip
from conda.cli import main_search
from conda.cli import main_share
from conda.cli import main_update
from conda.cli import main_skeleton
from conda.cli import main_config

# Borrowed from SymPy
from textwrap import fill, dedent
filldedent = lambda s, w=70: fill(dedent(str(s)).strip('\n'), width=w)

def main():
    if len(sys.argv) > 1 and sys.argv[1] in ('..activate', '..deactivate',
        '..changeps1', '..checkenv'):
        import conda.cli.activate as activate
        activate.main()
        return
    if len(sys.argv) == 1:
        sys.argv.append('-h')

    import logging
    import conda

    p = conda_argparse.ArgumentParser(
        description='conda is a tool for managing environments and packages.'
    )
    p.add_argument(
        '-V', '--version',
        action = 'version',
        version = 'conda %s' % conda.__version__,
    )
    p.add_argument(
        "--debug",
        action = "store_true",
        help = argparse.SUPPRESS,
    )
    sub_parsers = p.add_subparsers(
        metavar = 'command',
        dest = 'cmd',
    )

    main_info.configure_parser(sub_parsers)
    main_help.configure_parser(sub_parsers)
    main_list.configure_parser(sub_parsers)
    main_search.configure_parser(sub_parsers)
    main_create.configure_parser(sub_parsers)
    main_install.configure_parser(sub_parsers)
    main_update.configure_parser(sub_parsers)
    main_remove.configure_parser(sub_parsers)
    main_package.configure_parser(sub_parsers)
    main_pip.configure_parser(sub_parsers)
    main_skeleton.configure_parser(sub_parsers)
    main_share.configure_parser(sub_parsers)
    main_clone.configure_parser(sub_parsers)
    main_build.configure_parser(sub_parsers)
    main_index.configure_parser(sub_parsers)
    main_config.configure_parser(sub_parsers)

    args = p.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)

    try:
        args.func(args, p)
    except RuntimeError as e:
        sys.exit(filldedent("Error: %s" % e))
    except Exception as e:
        if e.__class__.__name__ not in ('ScannerError', 'ParserError'):
            print("""\
An unexpected error has occurred, please consider sending the
following traceback to the conda GitHub issue tracker at:

    https://github.com/ContinuumIO/conda/issues"

""")
        raise  # as if we did not catch it

# The above raise was:
#
#exc_info = sys.exc_info()
#raise exc_info[1], None, exc_info[2]
#
# But that syntax is not supported in py3k. Simply
# reraising (without argument!) should do the same. Try this:
#
# def foo():
#     bar()
# def bar():
#     1/0
# try:
#     foo()
# except Exception as e:
#     #raise e  # does not show traceback
#     raise  # Shows traceback as if we had not caught it


if __name__ == '__main__':
    main()
