# (c) 2012 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from argparse import RawDescriptionHelpFormatter

from conda.anaconda import Anaconda
from conda.config import ROOT_DIR
from conda.install import activated, deactivate
from conda.planners import create_remove_plan
from utils import (
    add_parser_prefix, add_parser_quiet, add_parser_yes, confirm, get_prefix
)


descr = "Remove a list of packages from a specified Anaconda environment."


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'remove',
        formatter_class = RawDescriptionHelpFormatter,
        description = descr,
        help        = descr,
        epilog      = remove_example,
    )
    add_parser_yes(p)
    p.add_argument(
        "--no-deps",
        action  = "store_true",
        help    = "do not follow and remove dependencies (default: false)",
    )
    add_parser_prefix(p)
    add_parser_quiet(p)
    p.add_argument(
        'package_names',
        metavar = 'package_name',
        action  = "store",
        nargs   = '+',
        help    = "package names to remove from Anaconda environment",
    )
    p.set_defaults(func=execute)


def execute(args, parser):
    conda = Anaconda()

    prefix = get_prefix(args)

    env = conda.lookup_environment(prefix)

    plan = create_remove_plan(env, args.package_names, not args.no_deps)

    if plan.empty():
        print 'No packages found to remove from environment: %s' % prefix
        return

    print
    print "Package plan for package removal in environment %s:" % prefix
    print plan

    confirm(args)

    plan.execute(env, not args.quiet)


remove_example = '''
examples:
    conda remove -n myenv scipy

'''
