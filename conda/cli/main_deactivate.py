# (c) 2012 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from os.path import abspath, expanduser, join

from anaconda import anaconda
from config import ROOT_DIR
from package_plan import create_deactivate_plan


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'deactivate',
        description     = "Deactivate packages in an Anaconda environment.",
        help            = "Deactivate packages in an Anaconda environment. (ADVANCED)",
    )
    p.add_argument(
        "--confirm",
        action  = "store",
        default = "yes",
        choices = ["yes", "no"],
        help    = "ask for confirmation before deactivating packages (default: yes)",
    )
    p.add_argument(
        "--dry-run",
        action  = "store_true",
        default = False,
        help    = "display packages to be deactivated, without actually executing",
    )
    npgroup = p.add_mutually_exclusive_group()
    npgroup.add_argument(
        '-n', "--name",
        action  = "store",
        help    = "deactivate from a named environment (in %s/envs)" % ROOT_DIR,
    )
    npgroup.add_argument(
        '-p', "--prefix",
        action  = "store",
        default = ROOT_DIR,
        help    = "deactivate from a specified environment (default: %s)" % ROOT_DIR,
    )
    p.add_argument(
        'canonical_names',
        action  = "store",
        metavar = 'canonical_name',
        nargs   = '+',
        help    = "canonical name of package to deactivate in the specified Anaconda environment",

    )
    p.set_defaults(func=execute)


def execute(args):
    conda = anaconda()

    if args.name:
        prefix = join(ROOT_DIR, 'envs', args.name)
    else:
        prefix = abspath(expanduser(args.prefix))

    env = conda.lookup_environment(prefix)

    plan = create_deactivate_plan(env, args.canonical_names)

    if plan.empty():
        print 'All packages already deactivated, nothing to do'
        if len(args.canonical_names) == 1:
            print "Could not find package with canonical name '%s' to deactivate (already deactivated or unknown)." % args.canonical_names[0]
        else:
            print "Could not find packages with canonical names %s to deactivate." % args.canonical_names
        return

    print plan

    if args.dry_run: return

    if args.confirm == "yes":
        proceed = raw_input("Proceed (y/n)? ")
        if proceed.lower() not in ['y', 'yes']: return

    plan.execute(env)



