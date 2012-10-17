from os.path import abspath, expanduser
from optparse import OptionParser

from anaconda import anaconda
from config import ROOT_DIR
from package_plan import create_download_plan


def main_download(args, display_help=False):
    p = OptionParser(
        usage       = "usage: conda download [options] packages",
        description = "Download Anaconda packages and their dependencies.",
    )
    p.add_option(
        '-p', "--prefix",
        action  = "store",
        default = ROOT_DIR,
        help    = "download packages compatible with a specified environment, defaults to %default",
    )
    p.add_option(
        '-n', "--no-deps",
        action  = "store_true",
        default = False,
        help    = "only download specified packages, no dependencies",
    )
    p.add_option(
        '-f', "--force",
        action  = "store_true",
        default = False,
        help    = "force package downloads even when specific package is already available",
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
        help    = "display packages to be modified, without actually executing",
    )
    p.add_option(
        "--no-confirm",
        action  = "store_true",
        default = False,
        help    = "download without confirmation",
    )

    if display_help:
        p.print_help()
        return

    opts, args = p.parse_args(args)

    if len(args) == 0:
        p.error('too few arguments')

    conda = anaconda()

    prefix = abspath(expanduser(opts.prefix))
    env = conda.lookup_environment(prefix)

    plan = create_download_plan(env, args, opts.no_deps, opts.force)

    if plan.empty():
        print 'All packages already downloaded, nothing to do'
        return

    print plan

    if opts.dry_run:
        return

    if not opts.no_confirm:
        proceed = raw_input("Proceed (y/n)? ")
        if proceed.lower() not in ['y', 'yes']: return

    progress_bar = not opts.no_progress_bar
    plan.execute(env, progress_bar)
