
from optparse import OptionParser
from os.path import abspath, expanduser

from anaconda import anaconda
from config import ROOT_DIR
from package_plan import create_deactivate_plan

def main_deactivate(args, display_help=False):
    p = OptionParser(
        usage       = "usage: conda remove [options] packages",
        description = "Deactivate packages in an Anaconda environment.",
    )
    p.add_option(
        '-p', "--prefix",
        action  = "store",
        default = ROOT_DIR,
        help    = "deactivate from a specified environment, defaults to %default",
    )
    p.add_option(
        '-f', "--follow-deps",
        action  = "store_true",
        default = False,
        help    = "deactivate dependencies automatically",
    )
    p.add_option(
        "--dry-run",
        action  = "store_true",
        default = False,
        help    = "display packages to be modified, without actually executing",
    )
    p.add_option(
        "--no-confirm",
        action  = "store_true",
        default = False,
        help    = "deactivate without confirmation",
    )

    if display_help:
        p.print_help()
        return

    opts, args = p.parse_args(args)

    if len(args) == 0:
        p.error('too few arguments')


    if opts.dry_run and opts.no_confirm:
        p.error('--dry-run and --no-confirm are incompatible')

    conda = anaconda()

    prefix = abspath(expanduser(opts.prefix))
    env = conda.lookup_environment(prefix)

    plan = create_deactivate_plan(env, args, opts.follow_deps)

    if plan.empty():
        print 'All packages already deactivated, nothing to do'
        return

    print plan

    if opts.dry_run: return

    if not opts.no_confirm:
        proceed = raw_input("Proceed (y/n)? ")
        if proceed.lower() not in ['y', 'yes']: return

    plan.execute(env)



