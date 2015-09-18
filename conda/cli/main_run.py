# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from __future__ import print_function, division, absolute_import

import sys
import logging

from conda.cli import common

descr = """
Launches an application installed with conda.

To include command line options in a command, separate the command from the
other options with --, like

    conda run -- ipython --matplotlib
"""

examples = """
Examples:

    conda run ipython-notebook
"""

def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'run',
        description=descr,
        help=descr,
        epilog=examples,
    )
    common.add_parser_prefix(p)
    common.add_parser_quiet(p)
    common.add_parser_json(p)
    common.add_parser_offline(p)
    p.add_argument(
        'package',
        metavar='COMMAND',
        action="store",
        nargs='?',
        help="Package to launch."
    )
    p.add_argument(
        'arguments',
        metavar='ARGUMENTS',
        action='store',
        nargs='*',
        help="Additional arguments to application."
    )
    p.set_defaults(func=execute)


def execute(args, parser):
    if not args.package:
        parser.print_help()
        return

    import conda.install
    import conda.resolve
    from conda.api import get_package_versions, app_is_installed
    from conda.misc import launch

    prefix = common.get_prefix(args)

    if args.quiet:
        logging.disable(logging.CRITICAL)

    if args.package.endswith('.tar.bz2'):
        if app_is_installed(args.package, prefixes=[prefix]):
            fn = args.package
        else:
            error_message = "Package {} not installed.".format(args.package)
            common.error_and_exit(error_message, json=args.json,
                                  error_type="PackageNotInstalled")
    else:
        installed = []
        for pkg in get_package_versions(args.package, args.offline):
            if app_is_installed(pkg.fn, prefixes=[prefix]):
                installed.append(pkg)

        for pkg in conda.install.linked(prefix):
            name, version, build = pkg.rsplit('-', 2)
            if name == args.package:
                installed = [conda.resolve.Package(pkg + '.tar.bz2',
                                                   conda.install.is_linked(prefix, pkg))]
                break

        if installed:
            package = max(installed)
            fn = package.fn

            try:
                subprocess = launch(fn, prefix=prefix,
                                    additional_args=args.arguments,
                                    background=args.json)
                if args.json:
                    common.stdout_json(dict(fn=fn, pid=subprocess.pid))
                elif not args.quiet:
                    print("Started app. Some apps may take a while to finish loading.")
            except TypeError:
                execute_command(args.package, prefix, args.arguments, args.json)
            except Exception as e:
                common.exception_and_exit(e, json=args.json)
        else:
            # Try interpreting it as a command
            execute_command(args.package, prefix, args.arguments, args.json)

def execute_command(cmd, prefix, additional_args, json=False):
    from conda.misc import execute_in_environment
    try:
        process = execute_in_environment(
            cmd, prefix=prefix, additional_args=additional_args, inherit=not json)
        if not json:
            sys.exit(process.wait())
        else:
            common.stdout_json(dict(cmd=cmd, pid=process.pid))
    except OSError:
        error_message = "App {} not installed.".format(cmd)
        common.error_and_exit(error_message, json=json,
                              error_type="AppNotInstalled")
