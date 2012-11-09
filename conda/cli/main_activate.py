
from os.path import abspath, expanduser

from anaconda import anaconda
from config import ROOT_DIR
from package_plan import create_activate_plan


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'activate',
        description     = "Activate available packages in the specified Anaconda enviropnment.",
        help            = "Activate available packages in the specified Anaconda enviropnment. (ADVANCED)",
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
        help    = "Anaconda environment to activate packages ini (default: %s)" % ROOT_DIR,
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
        print 'No packages found to activate, nothing to do'
        return

    print plan

    if args.dry_run: return

    if args.confirm == "yes":
        proceed = raw_input("Proceed (y/n)? ")
        if proceed.lower() not in ['y', 'yes']: return

    plan.execute(env)


