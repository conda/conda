
from argparse import ArgumentDefaultsHelpFormatter
from os import makedirs
from os.path import abspath, exists, expanduser, join

from anaconda import anaconda
from config import ROOT_DIR
from package_plan import create_create_plan
from requirement import requirement


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'create',
        description     = "Create an Anaconda environment at a specified prefix from a list of package specifications.",
        help            = "Create an Anaconda environment at a specified prefix from a list of package specifications.",
        formatter_class = ArgumentDefaultsHelpFormatter,
    )
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
        help    = "display packages to be activated, without actually executing",
    )
    p.add_argument(
        '-f', "--file",
        action  = "store",
        help    = "filename to read package specs from",
    )
    npgroup = p.add_mutually_exclusive_group(required=True)
    npgroup.add_argument(
        '-n', "--name",
        action  = "store",
        help    = "name of new directory (in %s/envs) to create Anaconda environment in" % ROOT_DIR,
    )
    npgroup.add_argument(
        '-p', "--prefix",
        action  = "store",
        help    = "full path of new directory to create Anaconda environment in",
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
        'package_specs',
        metavar = 'package_spec',
        action  = "store",
        nargs   ='*',
        help    = "package specification of package to install into new Anaconda environment",
    )
    p.set_defaults(func=execute)


def execute(args, parser):
    if len(args.package_specs) == 0 and not args.file:
        parser.error('too few arguments, must supply command line package specs or --file')

    conda = anaconda()

    if args.prefix:
        prefix = abspath(expanduser(args.prefix))
    else:
        prefix = join(ROOT_DIR, 'envs', args.name)
    env = conda.lookup_environment(prefix)

    if exists(prefix):
        if args.prefix:
            parser.error("'%s' already exists, must supply new directory for -p/--prefix" % prefix)
        else:
            parser.error("'%s' already exists, must supply new directory for -n/--name" % prefix)

    if args.file:
        try:
            f = open(abspath(args.file))
            req_strings = [line for line in f]
            f.close()
        except:
            parser.error('could not read file: %s', args.file)
    else:
        req_strings = args.package_specs

    reqs = set()
    for req_string in req_strings:
        try:
            reqs.add(requirement(req_string))
        except RuntimeError:
            candidates = conda.index.lookup_from_name(req_string)
            reqs = reqs | set(requirement(
                                "%s %s" % (pkg.name, pkg.version.vstring))
                                for pkg in candidates)

    try:
        plan = create_create_plan(prefix, conda, reqs, args.use_defaults=="yes")
    except RuntimeError as e:
        print "conda: error:", e
        return

    if plan.empty():
        print 'No matching packages could be found, nothing to do'
        return

    print plan

    if args.dry_run: return

    if args.confirm == "yes":
        proceed = raw_input("Proceed (y/n)? ")
        if proceed.lower() not in ['y', 'yes']: return

    makedirs(prefix)

    plan.execute(env, args.progress_bar=="yes")
