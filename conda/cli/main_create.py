from os import mkdir
from os.path import abspath, exists, expanduser
from optparse import OptionParser

from package_plan import create_create_plan
from requirement import requirement


def main_create(args, conda, display_help=False):
    p = OptionParser(
        usage       = "usage: conda create [options] [package versions]",
        description = "Create an Anaconda environment at a specified prefix from a list of package versions."
    )
    p.add_option(
        '-p', "--prefix",
        action  = "store",
        default = None,
        help    = "new directory to create environment in",
    )
    p.add_option(
        '-f', "--file",
        action  = "store",
        default = None,
        help    = "filename to read package versions from",
    )
    p.add_option(
        '-n', "--no-defaults",
        action  = "store_true",
        default = False,
        help    = "do not select default versions for unspecified requirements",
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
        help    = "create Anaconda environment without confirmation",
    )

    if display_help:
        p.print_help()
        return

    opts, args = p.parse_args(args)

    if len(args) == 0 and not opts.file:
        p.error('too few arguments, must supply command line packages '
                'versions or --file')

    if len(args) > 0 and opts.file:
        p.error('must supply command line packages, or --file, but not both')

    if not opts.prefix:
        p.error('must supply --prefix')

    prefix = abspath(expanduser(opts.prefix))
    env = conda.lookup_environment(prefix)

    if exists(prefix):
        p.error("'%s' already exists, must supply new directory for --prefix" %
                opts.prefix)

    if opts.file:
        try:
            f = open(abspath(opts.file))
            req_strings = [line for line in f]
            f.close()
        except:
            p.error('error reading file: %s', opts.file)
    else:
        req_strings = args

    reqs = set()
    for req_string in req_strings:
        try:
            reqs.add(requirement(req_string))
        except RuntimeError:
            candidates = conda.index.lookup_from_name(req_string)
            reqs = reqs | set(requirement(
                                "%s %s" % (pkg.name, pkg.version.vstring))
                                for pkg in candidates)

    plan = create_create_plan(prefix, conda, reqs, opts.no_defaults)

    if plan.empty():
        print 'No packages found, nothing to do'
        return

    print plan

    if opts.dry_run: return

    if not opts.no_confirm:
        proceed = raw_input("Proceed (y/n)? ")
        if proceed.lower() not in ['y', 'yes']: return

    mkdir(prefix)

    progress_bar = not opts.no_progress_bar
    plan.execute(env, progress_bar)
