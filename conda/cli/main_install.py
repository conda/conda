
from argparse import ArgumentDefaultsHelpFormatter
from os.path import abspath, exists, expanduser

from anaconda import anaconda
from config import ROOT_DIR
from package_plan import create_install_plan


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'install',
        description     = "Install a list of packages into a specified Anaconda environment.",
        help            = "Install a list of packages into a specified Anaconda environment.",
        formatter_class = ArgumentDefaultsHelpFormatter,
    )
    p.add_argument(
        "--confirm",
        action  = "store",
        default = "yes",
        choices = ["yes", "no"],
        help    = "ask for confirmation before installing packages into Anaconda environment",
    )
    p.add_argument(
        "--dry-run",
        action  = "store_true",
        default = False,
        help    = "display packages to be modified, without actually executing",
    )
    p.add_argument(
        '-f', "--file",
        action  = "store",
        help    = "filename to read package versions from",
    )
    p.add_argument(
        '-p', "--prefix",
        action  = "store",
        default = ROOT_DIR,
        help    = "Anaconda environment to install packages into",
    )
    p.add_argument(
        "--progress-bar",
        action  = "store",
        default = "yes",
        choices = ["yes", "no"],
        help    = "display progress bar for package downloads",
    )
    p.add_argument(
        'packages',
        metavar = 'package_version',
        action  = "store",
        nargs   = '*',
        help    = "package versions to install into Anaconda environment",
    )
    p.set_defaults(func=execute)

def execute(args, parser):
    pkg_versions = args.packages

    if len(pkg_versions) == 0 and not args.file:
        parser.error('too few arguments, must supply command line packages versions or --file')

    conda = anaconda()

    prefix = abspath(expanduser(args.prefix))
    env = conda.lookup_environment(prefix)

    if not exists(prefix):
        parser.error("'%s' is not a valid Anaconda environment" % args.prefix)

    if args.file:
        try:
            f = open(abspath(args.file))
            req_strings = [line for line in f]
            f.close()
        except:
            parser.error('could not read file: %s', args.file)
    else:
        req_strings = pkg_versions

    conda = anaconda()

    plan = create_install_plan(env, req_strings)

    if plan.empty():
        print 'No packages found, nothing to do'
        return

    print plan

    if args.dry_run: return

    if args.confirm == "yes":
        proceed = raw_input("Proceed (y/n)? ")
        if proceed.lower() not in ['y', 'yes']: return

    plan.execute(env, args.progress_bar=="yes")


