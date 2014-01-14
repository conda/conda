# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from __future__ import print_function, division, absolute_import

import os
from argparse import RawDescriptionHelpFormatter

from conda.cli import common
from conda.convert import show_cext, has_cext

import tarfile

help = "Various tools to convert conda packages."
example = ''

def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'convert',
        formatter_class = RawDescriptionHelpFormatter,
        description = help,
        help = help,
        epilog = example,
    )

    # TODO: Factor this into a subcommand, since it's python package specific
    p.add_argument(
        'package_file',
        metavar = 'package-file',
        action = "store",
        nargs = '+',
        help = "package versions to install into conda environment",
        )
    p.add_argument(
        '-p', "--platform",
        dest='platforms',
        action="append",
        choices=['osx-64', 'linux-32', 'linux-64', 'win-32', 'win-64'],
        required=True,
        help="Platform to convert the packages to",
        )
    p.add_argument(
        '--show-imports',
        action='store_true',
        default=False,
        help="Show Python imports for compiled parts of the package",
        )
    p.add_argument(
        '-f', "--force",
        action = "store_true",
        help = "force convert, even when a package has compiled C extensions",
    )

    p.set_defaults(func=execute)


def execute(args, parser):
    files = args.package_file

    for file in files:
        t = tarfile.open(file)

        if args.show_imports:
            show_cext(t)

        if not args.force and has_cext(t):
            print("WARNING: Package %s has C extensions, skipping. Use -f to "
            "force conversion." % file)
            continue

        for platform in args.platforms:
            print("Converting %s to %s" % (file, platform))
