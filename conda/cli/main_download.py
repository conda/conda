
from argparse import ArgumentDefaultsHelpFormatter
from os.path import abspath, expanduser

from anaconda import anaconda
from config import ROOT_DIR
from package_plan import create_download_plan


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'download',
        description     = "Download Anaconda packages and their dependencies.",
        help            = "Download Anaconda packages and their dependencies.",
        formatter_class = ArgumentDefaultsHelpFormatter,
    )
    p.add_argument(
        "--confirm",
        action  = "store",
        default = "yes",
        choices = ["yes", "no"],
        help    = "ask for confirmation before downloading packages",
    )
    p.add_argument(
        "--dry-run",
        action  = "store_true",
        default = False,
        help    = "display packages to be downloaded, without actually executing",
    )
    p.add_argument(
        '-f', "--force",
        action  = "store_true",
        default = False,
        help    = "force package downloads even when specific package is already available",
    )
    p.add_argument(
        '-n', "--no-deps",
        action  = "store_true",
        default = False,
        help    = "only download specified packages, no dependencies",
    )
    p.add_argument(
        '-p', "--prefix",
        action  = "store",
        default = ROOT_DIR,
        help    = "download packages compatible with the specified environment",
    )
    p.add_argument(
        "--progress-bar",
        action  = "store",
        default = "yes",
        choices = ["yes", "no"],
        help    = "display progress bar for package downloads",
    )
    p.add_argument(
        'canonical_names',
        action  = "store",
        metavar = 'canonical_name',
        nargs   = '+',
    )
    p.set_defaults(func=execute)


def execute(args, parser):
    conda = anaconda()

    prefix = abspath(expanduser(args.prefix))
    env = conda.lookup_environment(prefix)

    plan = create_download_plan(env, args.canonical_names, args.no_deps, args.force)

    if plan.empty():
        print 'All packages already downloaded, nothing to do'
        return

    print plan

    if args.dry_run:
        return

    if args.confirm == "yes":
        proceed = raw_input("Proceed (y/n)? ")
        if proceed.lower() not in ['y', 'yes']: return

    plan.execute(env, args.progress_bar=="yes")
