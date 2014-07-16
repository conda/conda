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

    build      : build a package from recipe
    package    : create a conda package in an environment
    index      : updates repodata.json in channel directories

Additional help for each command can be accessed by using:

    conda <command> -h
'''

from __future__ import print_function, division, absolute_import

import sys
import argparse

from conda.cli import conda_argparse
from conda.cli import main_bundle
from conda.cli import main_create
from conda.cli import main_help
from conda.cli import main_init
from conda.cli import main_info
from conda.cli import main_install
from conda.cli import main_list
from conda.cli import main_remove
from conda.cli import main_package
from conda.cli import main_search
from conda.cli import main_update
from conda.cli import main_config
from conda.cli import main_clean

def main():
    if len(sys.argv) > 1:
        argv1 = sys.argv[1]
        if argv1 in ('..activate', '..deactivate', '..activateroot', '..checkenv'):
            import conda.cli.activate as activate
            activate.main()
            return
        if argv1 in ('..changeps1'):
            import conda.cli.misc as misc
            misc.main()
            return
        if argv1 == 'pip':
            sys.exit("""ERROR:
The "conda pip" command has been removed from conda (as of version 1.8) for
the following reasons:
  * users get the wrong impression that you *must* use conda pip (instead
    of simply pip) when using Anaconda
  * there should only be one preferred way to build packages, and that is
    the conda build command
  * the command did too many things at once, i.e. build a package and
    then also install it
  * the command is Python centric, whereas conda (from a package management
    perspective) is Python agnostic
  * packages created with conda pip are not robust, i.e. they will maybe
    not work on other people's systems

In short:
  * use "conda build" if you want to build a conda package
  * use "conda install" if you want to install something
  * use "pip" if you want to install something that is on PyPI for which there
    isn't a conda package.
""")
        if argv1 in ('activate', 'deactivate'):
            sys.stderr.write("Error: '%s' is not a conda command.\n" % argv1)
            if sys.platform != 'win32':
                sys.stderr.write('Did you mean "source %s" ?\n' %
                                 ' '.join(sys.argv[1:]))
            sys.exit(1)

        # for backwards compatibility of conda-api
        if sys.argv[1:4] == ['share', '--json', '--prefix']:
            import json
            from os.path import abspath
            from conda.share import old_create_bundle
            prefix = sys.argv[4]
            path, warnings = old_create_bundle(abspath(prefix))
            json.dump(dict(path=path, warnings=warnings),
                      sys.stdout, indent=2, sort_keys=True)
            return
        if sys.argv[1:4] == ['clone', '--json', '--prefix']:
            import json
            from os.path import abspath
            from conda.share import old_clone_bundle
            prefix, path = sys.argv[4:6]
            old_clone_bundle(path, abspath(prefix))
            json.dump(dict(warnings=[]), sys.stdout, indent=2)
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
    main_config.configure_parser(sub_parsers)
    main_init.configure_parser(sub_parsers)
    main_clean.configure_parser(sub_parsers)
    main_package.configure_parser(sub_parsers)
    main_bundle.configure_parser(sub_parsers)

    try:
        import argcomplete
        argcomplete.autocomplete(p)
    except ImportError:
        pass
    except AttributeError:
        # On Python 3.3, argcomplete can be an empty namespace package when
        # we are in the conda-recipes directory.
        pass

    args = p.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)

    if (not main_init.is_initialized() and
        'init' not in sys.argv and 'info' not in sys.argv):
        sys.exit("""Error: conda is not initialized yet, try: conda init
# Note that initializing conda is not the recommended way for setting up your
# system.  The recommended way for setting up a conda system is by installing
# Miniconda, see: http://repo.continuum.io/miniconda/index.html""")

    args_func(args, p)

def args_func(args, p):
    try:
        args.func(args, p)
    except RuntimeError as e:
        sys.exit("Error: %s" % e)
    except Exception as e:
        if e.__class__.__name__ not in ('ScannerError', 'ParserError'):
            print("""\
An unexpected error has occurred, please consider sending the
following traceback to the conda GitHub issue tracker at:

    https://github.com/conda/conda/issues

Include the output of the command 'conda info' in your report.

""")
        raise  # as if we did not catch it

if __name__ == '__main__':
    main()
