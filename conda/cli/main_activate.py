
from optparse import OptionParser
from os.path import abspath, expanduser

from package_plan import create_activate_plan


def main_activate(args, conda, display_help=False):
    p = OptionParser(
        usage       = "usage: conda activate [options] [packages]",
        description = "Activate available packages in the specified Anaconda enviropnment."
    )
    p.add_option(
        '-p', "--prefix",
        action  = "store",
        default = conda.root_dir,
        help    = "environment to activate packages in, defaults to %default",
    )
    p.add_option(
        '-f', "--follow-deps",
        action  = "store_true",
        default = False,
        help    = "activate dependencies automatically",
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
        help    = "activate without confirmation",
    )

    if display_help:
        p.print_help()
        return

    opts, args = p.parse_args(args)

    if len(args) == 0:
        p.error('too few arguments')

    if opts.dry_run and opts.quiet:
        p.error('--dry-run and --quiet are mutually exclusive')

    env = conda.lookup_environment(abspath(expanduser(opts.prefix)))
    plan = create_activate_plan(env, args, opts.follow_deps)

    if plan.empty():
        if not opts.quiet:
            print 'No packages found to activate, nothing to do'
        return

    print plan

    if opts.dry_run: return

    if opts.no_confirm:
        proceed = raw_input("Proceed (y/n)? ")
        if proceed.lower() not in ['y', 'yes']: return

    plan.execute(conda.lookup_environment(opts.prefix))


