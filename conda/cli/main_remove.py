# (c) 2012 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from argparse import RawDescriptionHelpFormatter

from conda.install import activated, deactivate
from utils import (
    add_parser_prefix, add_parser_quiet, add_parser_yes, get_prefix
)


descr = "Remove a list of packages from a specified Anaconda environment."


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'remove',
        formatter_class = RawDescriptionHelpFormatter,
        description = descr,
        help        = descr,
    )
    add_parser_yes(p)
    p.add_argument(
        '-f', "--force",
        action  = "store_true",
        help    = "force remoing package (no dependency checking)",
    )
    add_parser_prefix(p)
    add_parser_quiet(p)
    p.add_argument(
        'packages',
        metavar = 'name',
        action  = "store",
        nargs   = '+',
        help    = "package names to remove from Anaconda environment",
    )
    p.set_defaults(func=execute)


def execute(args):
    prefix = get_prefix(args)

    if args.force and args.yes:
        for dist in activated(prefix):
            pkg_name = dist.rsplit('-', 2)[0]
            if pkg_name in args.packages:
                print "removing:", dist
                deactivate(dist, prefix)
    else:
        raise RuntimeError("Not implemented yet, only --force in combination "
                           "with --yes currently work")
