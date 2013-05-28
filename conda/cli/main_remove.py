# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from argparse import RawDescriptionHelpFormatter

import utils


help = "Remove a list of packages from a specified conda environment."
descr = help + """
When the special package_name 'ALL' is used all packages are
removed from the environment, i.e. the environment is removed.
"""
example = """
examples:
    conda remove -n myenv scipy

"""

def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'remove',
        formatter_class = RawDescriptionHelpFormatter,
        description = descr,
        help = help,
        epilog = example,
    )
    utils.add_parser_yes(p)
    #p.add_argument(
    #    "--no-deps",
    #    action  = "store_true",
    #    help    = "do not follow and remove dependencies (default: false)",
    #)
    p.add_argument(
        "--features",
        action = "store_true",
        help = "remove features (instead of packages)",
    )
    utils.add_parser_prefix(p)
    utils.add_parser_quiet(p)
    p.add_argument(
        'package_names',
        metavar = 'package_name',
        action = "store",
        nargs = '+',
        help = "package names to remove from environment",
    )
    p.set_defaults(func=execute)


def execute(args, parser):
    import conda.plan as plan
    from conda.api import get_index


    prefix = utils.get_prefix(args)
    if args.features:
        index = get_index()
        features = set(args.package_names)
        actions = plan.remove_features_actions(prefix, index, features)
    else:
        specs = utils.specs_from_args(args.package_names)
        actions = plan.remove_actions(prefix, specs)

    if plan.nothing_to_do(actions):
        print 'No packages found to remove from environment: %s' % prefix
        return

    print
    print "Package plan for package removal in environment %s:" % prefix
    plan.display_actions(actions)

    utils.confirm(args)
    plan.execute_actions(actions, enable_progress=not args.quiet)
