
from argparse import ArgumentDefaultsHelpFormatter
from os.path import abspath, expanduser

from anaconda import anaconda
from config import ROOT_DIR
from package_plan import create_deactivate_plan


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'deactivate',
        description     = "Deactivate packages in an Anaconda environment.",
        help            = "Deactivate packages in an Anaconda environment. (ADVANCED)",
        formatter_class = ArgumentDefaultsHelpFormatter,
    )
    p.add_argument(
        "--confirm",
        action  = "store",
        default = "yes",
        choices = ["yes", "no"],
        help    = "ask for confirmation before deactivating packages",
    )
    p.add_argument(
        "--dry-run",
        action  = "store_true",
        default = False,
        help    = "display packages to be deactivated, without actually executing",
    )
    p.add_argument(
        '-p', "--prefix",
        action  = "store",
        default = ROOT_DIR,
        help    = "deactivate from a specified environment",
    )
    p.add_argument(
        'canonical_names',
        action  = "store",
        metavar = 'canonical_name',
        nargs   = '+',
        help    = "canonical name of package to deactivate in the specified Anaconda environment",

    )
    p.set_defaults(func=execute)


def execute(args, parser):
    conda = anaconda()

    prefix = abspath(expanduser(args.prefix))
    env = conda.lookup_environment(prefix)

    plan = create_deactivate_plan(env, args.canonical_names)

    if plan.empty():
        print 'All packages already deactivated, nothing to do'
        return

    print plan

    if args.dry_run: return

    if args.confirm == "yes":
        proceed = raw_input("Proceed (y/n)? ")
        if proceed.lower() not in ['y', 'yes']: return

    plan.execute(env)



