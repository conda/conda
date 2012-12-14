# (c) 2012 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

import re

from conda.anaconda import anaconda
from conda.package import sort_packages_by_name
from utils import add_parser_prefix, get_prefix


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'list',
        description = "List activated packages in an Anaconda environment.",
        help        = "List activated packages in an Anaconda environment.",
    )
    add_parser_prefix(p)
    p.add_argument(
        '-c', "--canonical",
        action  = "store_true",
        default = False,
        help    = "output canonical names of packages only",
    )
    p.add_argument(
        'search_expression',
        action  = "store",
        nargs   = "?",
        help    = "list only packages matching this regular expression",
    )
    p.set_defaults(func=execute)


def execute(args):
    conda = anaconda()

    prefix = get_prefix(args)

    env = conda.lookup_environment(prefix)

    matching = ""
    pkgs = env.activated
    if args.search_expression:
        try:
            pat = re.compile(args.search_expression)
        except:
            raise RuntimeError("Could not understand search expression '%s'" %
                               args.search_expression)
        matching = " matching '%s'" % args.search_expression
        pkgs = [pkg for pkg in env.activated if pat.search(pkg.name)]

    if args.canonical:
        for pkg in sort_packages_by_name(pkgs):
            print pkg.canonical_name
        return

    if len(pkgs) == 0:
        print('no packages%s found in environment at %s:' %
              (matching, env.prefix))
        return

    print 'packages%s in environment at %s:' % (matching, env.prefix)
    print
    for pkg in sort_packages_by_name(pkgs):
        print '%-25s %s' % (pkg.name, pkg.version)
