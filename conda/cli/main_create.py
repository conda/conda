
from argparse import ArgumentDefaultsHelpFormatter
from os import mkdir
from os.path import abspath, exists, expanduser

from anaconda import anaconda
from package_plan import create_create_plan
from requirement import requirement


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'create',
        description     = "Create an Anaconda environment at a specified prefix from a list of package versions.",
        help            = "Create an Anaconda environment at a specified prefix from a list of package versions.",
        formatter_class = ArgumentDefaultsHelpFormatter,
    )
    group = p.add_mutually_exclusive_group()
    p.add_argument(
        "--confirm",
        action  = "store",
        default = "yes",
        choices = ["yes", "no"],
        help    = "ask for confirmation before creating Anaconda environment",
    )
    p.add_argument(
        "--dry-run",
        action  = "store_true",
        default = False,
        help    = "display packages to be modified, without actually executing",
    )
    group.add_argument(
        '-f', "--file",
        action  = "store",
        help    = "filename to read package versions from",
    )
    group.add_argument(
        '-p', "--packages",
        action  = "store",
        metavar = 'package_version',
        nargs   = '*',
        help    = "package versions to install into new Anaconda environment",
    )
    p.add_argument(
        "--progress-bar",
        action  = "store",
        default = "yes",
        choices = ["yes", "no"],
        help    = "display progress bar for package downloads",
    )
    p.add_argument(
        "--use-defaults",
        action  = "store",
        default = "yes",
        choices = ["yes", "no"],
        help    = "select default versions for unspecified requirements when possible",
    )
    p.add_argument(
        'prefix',
        action  = "store",
        help    = "new directory to create Anaconda environment in",
    )
    p.set_defaults(func=execute)


def execute(args, parser):
    pkg_versions = args.packages

    if len(pkg_versions) == 0 and not args.file:
        parser.error('too few arguments, must supply command line packages versions or --file')

    conda = anaconda()

    prefix = abspath(expanduser(args.prefix))
    env = conda.lookup_environment(prefix)

    if exists(prefix):
        parser.error("'%s' already exists, must supply new directory for --prefix" % args.prefix)

    if args.file:
        try:
            f = open(abspath(args.file))
            req_strings = [line for line in f]
            f.close()
        except:
            parser.error('could not read file: %s', args.file)
    else:
        req_strings = pkg_versions

    reqs = set()
    for req_string in req_strings:
        try:
            reqs.add(requirement(req_string))
        except RuntimeError:
            candidates = conda.index.lookup_from_name(req_string)
            reqs = reqs | set(requirement(
                                "%s %s" % (pkg.name, pkg.version.vstring))
                                for pkg in candidates)

    plan = create_create_plan(prefix, conda, reqs, args.use_defaults=="yes")

    if plan.empty():
        print 'No packages found, nothing to do'
        return

    print plan

    if args.dry_run: return

    if args.confirm == "yes":
        proceed = raw_input("Proceed (y/n)? ")
        if proceed.lower() not in ['y', 'yes']: return

    mkdir(prefix)

    plan.execute(env, args.progress_bar=="yes")
