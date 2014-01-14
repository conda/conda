# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from __future__ import print_function, division, absolute_import

import tarfile

from os.path import abspath, expanduser, split, join
from argparse import RawDescriptionHelpFormatter

from conda.convert import has_cext, tar_update

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
        action="store_true",
        help="Force convert, even when a package has compiled C extensions",
    )
    p.add_argument(
        '-o', '--output-dir',
        default=None,
        help="Directory to write the output files (default is the same "
        "directory as the input file",
    )
    p.add_argument(
        '-v', '--verbose',
        default=False,
        action='store_true',
        help="Print verbose output"
        )

    p.set_defaults(func=execute)


def execute(args, parser):
    files = args.package_file

    for file in files:
        if not file.endswith('.tar.bz2'):
            raise RuntimeError("%s does not appear to be a conda package" % file)

        file = abspath(expanduser(file))
        t = tarfile.open(file)
        cext = False
        if args.show_imports:
            cext = has_cext(t, show=True)

        if not args.force and (cext or has_cext(t)):
            print("WARNING: Package %s has C extensions, skipping. Use -f to "
            "force conversion." % file)
            continue

        output_dir = args.output_dir or split(file)[0]
        fn = split(file)[1]
        for platform in args.platforms:
            members = t.getmembers()
            file_map = {}
            for member in members:
                file_map[member.path] = member

            print("Converting %s to %s" % (file, platform))
            tar_update(t, join(output_dir, fn), file_map, verbose=args.verbose)
