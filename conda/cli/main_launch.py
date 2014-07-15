# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from __future__ import print_function, division, absolute_import

import sys

from conda.cli import common

descr = "Launches an application installed with Conda."

def configure_parser(sub_parsers):
    p = sub_parsers.add_parser('launch',
                               description = descr,
                               help = descr)
    common.add_parser_prefix(p)
    common.add_parser_json(p)
    p.add_argument(
        'package',
        metavar = 'COMMAND',
        action = "store",
        nargs = '?',
        help = "package to launch"
    )
    p.set_defaults(func=execute)


def execute(args, parser):
    if not args.package:
        parser.print_help()
        return

    from conda.api import get_package_versions, app_is_installed
    from conda.misc import launch

    prefix = common.get_prefix(args)

    if args.package.endswith('.tar.bz2'):
        if app_is_installed(args.package, prefixes=[prefix]):
            fn = args.package
        else:
            error_message = "Package {} not installed.".format(args.package)
            common.error_and_exit(error_message, json=args.json,
                                  error_type="PackageNotInstalled")
    else:
        installed = []
        for pkg in get_package_versions(args.package):
            if app_is_installed(pkg.fn, prefixes=[prefix]):
                installed.append(pkg)

        if not installed:
            error_message = "App {} not installed.".format(args.package)
            common.error_and_exit(error_message, json=args.json,
                                  error_type="AppNotInstalled")

        package = max(installed)
        fn = package.fn

    try:
        subprocess = launch(fn, prefix=prefix)
        if args.json:
            common.stdout_json(dict(fn=fn))
        else:
            print("Started app. Some apps may take a while to finish loading.")
    except Exception as e:
        common.exception_and_exit(e, json=args.json)
