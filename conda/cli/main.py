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

import os
import subprocess
import sys
import traceback

def main():
    if len(sys.argv) > 1:
        argv1 = sys.argv[1]
        if argv1 in ('..activate', '..deactivate',
                     '..activateroot', '..checkenv'):
            import conda.cli.activate as activate
            activate.main()
            return
        if argv1 in ('..changeps1'):
            import conda.cli.misc as misc
            misc.main()
            return
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
    from conda.cli import conda_argparse
    import argparse
    import conda

    p = conda_argparse.ArgumentParser(
        description='conda is a tool for managing and deploying applications, environments and packages.'
    )
    p.add_argument(
        '-V', '--version',
        action='version',
        version='conda %s' % conda.__version__,
        help="Show the conda version number and exit."
    )
    p.add_argument(
        "--debug",
        action = "store_true",
        help = "Show debug output."
    )
    p.add_argument(
        "--json",
        action = "store_true",
        help = argparse.SUPPRESS,
    )
    sub_parsers = p.add_subparsers(
        metavar = 'command',
        dest = 'cmd',
    )

    from conda.cli import main_info
    main_info.configure_parser(sub_parsers)
    from conda.cli import main_help
    main_help.configure_parser(sub_parsers)
    from conda.cli import main_list
    main_list.configure_parser(sub_parsers)
    from conda.cli import main_search
    main_search.configure_parser(sub_parsers)
    from conda.cli import main_create
    main_create.configure_parser(sub_parsers)
    from conda.cli import main_install
    main_install.configure_parser(sub_parsers)
    from conda.cli import main_update
    main_update.configure_parser(sub_parsers)
    main_update.configure_parser(sub_parsers, name='upgrade')
    from conda.cli import main_remove
    main_remove.configure_parser(sub_parsers)
    main_remove.configure_parser(sub_parsers, name='uninstall')
    from conda.cli import main_run
    main_run.configure_parser(sub_parsers)
    from conda.cli import main_config
    main_config.configure_parser(sub_parsers)
    from conda.cli import main_init
    main_init.configure_parser(sub_parsers)
    from conda.cli import main_clean
    main_clean.configure_parser(sub_parsers)
    from conda.cli import main_package
    main_package.configure_parser(sub_parsers)
    from conda.cli import main_bundle
    main_bundle.configure_parser(sub_parsers)

    from conda.cli.find_commands import find_commands
    sub_parsers.completer = lambda prefix, **kwargs: [i for i in
        list(sub_parsers.choices) + find_commands() if i.startswith(prefix)]
    args = p.parse_args()

    if getattr(args, 'json', False):
        # Silence logging info to avoid interfering with JSON output
        for logger in logging.Logger.manager.loggerDict:
            if logger not in ('fetch', 'progress'):
                logging.getLogger(logger).setLevel(logging.CRITICAL + 1)

    if args.debug:
        logging.disable(logging.NOTSET)
        logging.basicConfig(level=logging.DEBUG)

    if (not main_init.is_initialized() and
        'init' not in sys.argv and 'info' not in sys.argv):
        if hasattr(args, 'name') and hasattr(args, 'prefix'):
            import conda.config as config
            from conda.cli import common
            if common.get_prefix(args) == config.root_dir:
                sys.exit("""\
Error: This installation of conda is not initialized. Use 'conda create -n
envname' to create a conda environment and 'source activate envname' to
activate it.

# Note that pip installing conda is not the recommended way for setting up your
# system.  The recommended way for setting up a conda system is by installing
# Miniconda, see: http://repo.continuum.io/miniconda/index.html""")

    args_func(args, p)

def args_func(args, p):
    from conda.cli import common
    if os.name == 'nt':
        print('Debug: print tasklist /V before main func:')
        print_task_list()
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

def print_task_list():
    if os.name != 'nt':
        return
    try:
        import psutil
    except ImportError:
        psutil = None
    print('tasklist /V')
    proc = subprocess.Popen(['cmd', '/c', 'tasklist','/V'])
    proc.wait()
    if psutil is None:
        return
    for proc in psutil.process_iter():
        if proc.pid == os.getpid():
            continue
        try:
            exe = proc.exe()
        except psutil.AccessDenied:
            print('AccessDenied on ', proc.pid)
            exe = None
        try:
            cmdline = proc.cmdline()
        except psutil.AccessDenied:
            cmdline = None
        try:
            open_files = proc.open_files()
        except psutil.AccessDenied:
            open_files = None
        template = '''PID: {}
        exe: {},
        cmdline: {},
        open_files: {}'''
        if exe:
            print(template.format(proc.pid, exe, cmdline, open_files))
        if open_files:
            for f in open_files:
                if f.startswith(sys.prefix):
                    print('Open file: ', f, 'is on sys.prefix.')

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
        common.error_and_exit(message + traceback.format_exc(),
                              error_type="UnexpectedError", json=True)
    print(message)
    if getattr(e, 'errno', None) == 13:

        print("""
    Review this tasklist /V output to find
    possible source of permissions error.
    One process may be holding onto the named file.

""")
        print_task_list()
if __name__ == '__main__':
    main()
