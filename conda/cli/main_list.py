# (c) 2012 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from os.path import abspath, expanduser, join
import re

from anaconda import anaconda
from config import ROOT_DIR
from package import sort_packages_by_name


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'list',
        description = "List activated packages in an Anaconda environment.",
        help        = "List activated packages in an Anaconda environment.",
    )
    npgroup = p.add_mutually_exclusive_group()
    npgroup.add_argument(
        '-n', "--name",
        action  = "store",
        help    = "name of new directory (in %s/envs) to list packages in" %
                  ROOT_DIR,
    )
    npgroup.add_argument(
        '-p', "--prefix",
        action  = "store",
        default = ROOT_DIR,
        help    = "full path to Anaconda environment to list packages in "
                  "(default: %s)" % ROOT_DIR,
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

    if args.name:
        prefix = join(ROOT_DIR, 'envs', args.name)
    else:
        prefix = abspath(expanduser(args.prefix))

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

    if len(pkgs) == 0:
        print('no packages and %s found in environment at %s:' %
              (matching, env.prefix))
        return

    print 'packages%s in environment at %s:' % (matching, env.prefix)
    print
    for pkg in sort_packages_by_name(pkgs):
        print '%-25s %-20s %s' % (pkg.name, pkg.version, pkg.build)
