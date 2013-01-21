# (c) 2012 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from argparse import RawDescriptionHelpFormatter
from os.path import isdir, join
from shutil import rmtree

from conda.anaconda import Anaconda
from conda.planners import create_activate_plan, create_deactivate_plan
from utils import add_parser_prefix, add_parser_yes, confirm, get_prefix


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'env',
        formatter_class = RawDescriptionHelpFormatter,
        description     = "Activate or deactivate available packages in the specified Anaconda environment.",
        help            = "Activate or deactivate available packages in the specified Anaconda environment. (ADVANCED)",
        epilog          = env_example,
    )
    add_parser_yes(p)
    add_parser_prefix(p)
    adr_group = p.add_mutually_exclusive_group()
    adr_group.add_argument(
        '-a', "--activate",
        action  = "store_true",
        default = False,
        help    = "activate available packages in the specified Anaconda environment.",
    )
    adr_group.add_argument(
        '-d', "--deactivate",
        action  = "store_true",
        default = False,
        help    = "deactivate packages in an Anaconda environment.",
    )
    adr_group.add_argument(
        '-r', "--remove",
        action  = "store_true",
        default = False,
        help    = "delete an Anaconda environment.",
    )
    p.add_argument(
        'canonical_names',
        action  = "store",
        metavar = 'canonical_name',
        nargs   = '*',
        help    = "canonical name of package to deactivate in the specified Anaconda environment",
    )
    p.set_defaults(func=execute)


def execute(args):
    conda = Anaconda()

    prefix = get_prefix(args)
    env = conda.lookup_environment(prefix)

    if args.activate:
        if not args.canonical_names:
            raise RuntimeError("must supply one or more canonical package names for -a/--activate")

        plan = create_activate_plan(env, args.canonical_names)

        if plan.empty():
            if len(args.canonical_names) == 1:
                print "Could not find package with canonical name '%s' to activate (already activated or unknown)." % args.canonical_names[0]
            else:
                print "Could not find packages with canonical names %s to activate." % args.canonical_names
            return

        print plan

        confirm(args)

        try:
            plan.execute(env)
        except IOError:
            raise RuntimeError('One of more of the packages is not locally available, see conda download -h')

    elif args.deactivate:
        if not args.canonical_names:
            raise RuntimeError("must supply one or more canonical package names for -d/--deactivate")

        plan = create_deactivate_plan(env, args.canonical_names)

        if plan.empty():
            print 'All packages already deactivated, nothing to do'
            if len(args.canonical_names) == 1:
                print "Could not find package with canonical name '%s' to deactivate (already deactivated or unknown)." % args.canonical_names[0]
            else:
                print "Could not find packages with canonical names %s to deactivate." % args.canonical_names
            return

        print plan

        confirm(args)

        plan.execute(env)

    elif args.remove:

        if args.canonical_names:
            raise RuntimeError("-r/--remove does not accept any canonical package names (use -p/--prefix or -n/--name to specify the environment to remove)")

        if env == conda.root_environment:
            raise RuntimeError("Cannot delete Anaconda root environment")

        if not isdir(join(env.prefix, 'conda-meta')):
            raise RuntimeError("%s does not appear to be an Anaconda environment" % env.prefix)

        print
        print "**** The following Anaconda environment directory will be removed: %s ****" % env.prefix
        print

        confirm(args)

        rmtree(env.prefix)

    else:
        raise RuntimeError("One of -a/--activate, -d/--deactivate or -r/--remove is required.")

env_example = '''
examples:
  conda env -ap ~/anaconda/envs/myenv numba-0.3.1-np17py27_0

  conda env -dp ~/anaconda/envs/myenv numba-0.3.1-np17py27_0

'''
