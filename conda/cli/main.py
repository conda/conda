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
import sys
import argparse

import conda_argparse
import main_build
import main_clone
import main_create
import main_help
import main_index
import main_info
import main_install
import main_list
import main_remove
import main_package
import main_pip
import main_search
import main_share
import main_update

from conda.lock import Locked

def main():
    if len(sys.argv) > 1 and sys.argv[1] in ('..activate', '..deactivate', '..changeps1'):
        import activate
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
    main_share.configure_parser(sub_parsers)
    main_clone.configure_parser(sub_parsers)
    main_build.configure_parser(sub_parsers)
    main_index.configure_parser(sub_parsers)

    args = p.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)

    try:
        with Locked():
            args.func(args, p)
    except RuntimeError as e:
        sys.exit("Error: %s" % e)
    except Exception as e:
        if e.__class__.__name__ not in ('ScannerError', 'ParserError'):
            print """\
An unexpected error has occurred, please consider sending the
following traceback to the conda GitHub issue tracker at:

    https://github.com/ContinuumIO/conda/issues"

"""
        exc_info = sys.exc_info()
        raise exc_info[1], None, exc_info[2]


if __name__ == '__main__':
    main()
