# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from argparse import RawDescriptionHelpFormatter

from utils import (add_parser_prefix, add_parser_quiet, add_parser_yes,
                   confirm, get_prefix)


descr = "Update conda packages."
example = """
examples:
    conda update -p ~/anaconda/envs/myenv scipy

"""

def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'update',
        formatter_class = RawDescriptionHelpFormatter,
        description = descr,
        help = descr,
        epilog = example,
    )
    add_parser_yes(p)
    add_parser_prefix(p)
    add_parser_quiet(p)
    p.add_argument(
        'pkg_names',
        metavar = 'package_names',
        action = "store",
        nargs = '*',
        help = "names of packages to update (default: anaconda)",
    )
    p.set_defaults(func=execute)


def execute(args, parser):
    import sys

    import conda.install as ci
    import conda.plan as plan
    from conda.api import get_index


    if len(args.pkg_names) == 0:
        args.pkg_names.append('anaconda')

    prefix = get_prefix(args)
    index = get_index()
    linked = set(plan.name_dist(d) for d in ci.linked(prefix))
    for name in args.pkg_names:
        for c in '= !@#$%^&*()<>?':
            if c in name:
                sys.exit("Invalid character '%s' in package "
                         "name: '%s'" % (c, name))
        if name not in linked:
            sys.exit("Error: package '%s' is not installed" % name)

    actions = plan.install_actions(prefix, index, args.pkg_names)

    if plan.nothing_to_do(actions):
        print 'All packages already at latest version, nothing to do'
        return

    print "Updating Anaconda environment at %s" % prefix
    plan.display_actions(actions)

    confirm(args)
    plan.execute_actions(actions, index, enable_progress=not args.quiet)
