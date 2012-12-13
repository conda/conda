# (c) 2012 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from argparse import RawDescriptionHelpFormatter

from conda.anaconda import anaconda
from conda.planners import create_update_plan
from utils import add_parser_prefix, get_prefix


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'update',
        formatter_class = RawDescriptionHelpFormatter,
        description     = "Update Anaconda packages.",
        help            = "Update Anaconda packages.",
        epilog          = activate_example,
    )
    p.add_argument(
        "--confirm",
        action  = "store",
        default = "yes",
        choices = ["yes", "no"],
        help    = "ask for confirmation before updating packages (default: yes)",
    )
    p.add_argument(
        "--dry-run",
        action  = "store_true",
        default = False,
        help    = "display packages to be modified, without actually exectuting",
    )
    add_parser_prefix(p)
    p.add_argument(
        'pkg_names',
        metavar = 'package_name',
        action  = "store",
        nargs   = '+',
        help    = "names of packages to update (default: all packages)",
    )
    p.set_defaults(func=execute)


def execute(args):
    conda = anaconda()

    if conda.local_index_only:
        raise RuntimeError('Updating packages requires access to package indices on remote package repositories. (Check network connection?)')

    prefix = get_prefix(args)

    env = conda.lookup_environment(prefix)

    plan = create_update_plan(env, args.pkg_names)

    if plan.empty():
        print 'All packages already at latest version'
        return

    print "Updating Anaconda environment at %s" % args.prefix

    print plan

    if args.dry_run: return

    if args.confirm == "yes":
        proceed = raw_input("Proceed (y/n)? ")
        if proceed.lower() not in ['y', 'yes']: return

    plan.execute(env)

activate_example = '''
examples:
    conda update -p ~/anaconda/envs/myenv scipy

'''
