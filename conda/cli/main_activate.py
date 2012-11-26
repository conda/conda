# (c) 2012 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from os.path import abspath, expanduser

from anaconda import anaconda
from config import ROOT_DIR
from package_plan import create_activate_plan


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'activate',
        description     = "Activate available packages in the specified Anaconda environment.",
        help            = "Activate available packages in the specified Anaconda environment. (ADVANCED)",
    )
    p.add_argument(
        "--confirm",
        action  = "store",
        default = "yes",
        choices = ["yes", "no"],
        help    = "ask for confirmation before activating packages in Anaconda environment (default: yes)",
    )
    p.add_argument(
        "--dry-run",
        action  = "store_true",
        default = False,
        help    = "display packages to be modified, without actually executing",
    )
    p.add_argument(
        '-p', "--prefix",
        action  = "store",
        default = ROOT_DIR,
        help    = "Anaconda environment to activate packages in (default: %s)" % ROOT_DIR,
    )
    p.add_argument(
        'canonical_names',
        metavar = 'canonical_name',
        action  = "store",
        nargs   = '+',
        help    = "canonical name of package to activate in the specified Anaconda environment",
    )
    p.set_defaults(func=execute)


def execute(args):
    conda = anaconda()

    prefix = abspath(expanduser(args.prefix))
    env = conda.lookup_environment(prefix)

    plan = create_activate_plan(env, args.canonical_names)

    if plan.empty():
        if len(args.canonical_names) == 1:
            print "Could not find package with canonical name '%s' to activate (already activated or unknown)." % args.canonical_names[0]
        else:
            print "Could not find packages with canonical names %s to activate." % args.canonical_names
        return

    print plan

    if args.dry_run: return

    if args.confirm == "yes":
        proceed = raw_input("Proceed (y/n)? ")
        if proceed.lower() not in ['y', 'yes']: return

    try:
        plan.execute(env)
    except IOError:
        raise RuntimeError('One of more of the packages is not locally available, see conda download -h')


