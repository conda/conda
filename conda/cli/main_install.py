
from os.path import abspath, exists, expanduser
from optparse import OptionParser

from package_plan import create_install_plan


def main_install(args, conda, display_help=False):
    p = OptionParser(
        usage       = "usage: conda install [options] [package versions]",
        description = "Create an Anaconda environment at a specified prefix from a list of package versions."
    )
    p.add_option(
        '-p', "--prefix",
        action  = "store",
        default = None,
        help    = "new directory to create environment in",
    )
    p.add_option(
        "--no-progress-bar",
        action  = "store_true",
        default = False,
        help    = "do not display progress bar for any downloads",
    )
    p.add_option(
        "--dry-run",
        action  = "store_true",
        default = False,
        help    = "display packages to be modified, without actually exectuting",
    )
    p.add_option(
        "--no-confirm",
        action  = "store_true",
        default = False,
        help    = "create Anaconda environment without confirmation",
    )
    p.add_option(
        '-f', "--file",
        action  = "store",
        default = None,
        help    = "filename to read package versions from",
    )

    if display_help:
        p.print_help()
        return

    opts, args = p.parse_args(args)

    if len(args) == 0 and not opts.file:
        p.error('too few arguments, must supply command line packages versions or --file')

    if len(args) > 0 and opts.file:
        p.error('must supply command line packages, or --file, but not both')

    if not opts.prefix:
        p.error('must supply --prefix')

    if not exists(abspath(opts.prefix)):
        p.error("'%s' is not a valid Anaconda environment`" % opts.prefix)

    if opts.dry_run and opts.quiet:
        p.error('--dry-run and --quiet are mutually exclusive')

    if opts.file:
        try:
            f = open(abspath(opts.file))
            args = [line for line in f]
            f.close()
        except:
            p.error('error reading file: %s', opts.file)

    env = conda.lookup_environment(abspath(expanduser(opts.prefix)))
    plan = create_install_plan(env, args)

    if plan.empty():
        if not opts.quiet:
            print 'No packages found, nothing to do'
        return

    print plan

    if opts.dry_run: return

    if opts.no_confirm:
        proceed = raw_input("Proceed (y/n)? ")
        if proceed.lower() not in ['y', 'yes']: return

    plan.execute(conda.lookup_environment(opts.prefix), opts.no_progress_bar)


