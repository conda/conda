
from os.path import abspath, expanduser, join

from anaconda import anaconda
from config import ROOT_DIR
from package import sort_packages_by_name


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'list',
        description     = "List activated packages in an Anaconda environment.",
        help            = "List activated packages in an Anaconda environment.",
    )
    npgroup = p.add_mutually_exclusive_group()
    npgroup.add_argument(
        '-n', "--name",
        action  = "store",
        help    = "name of new directory (in %s/envs) to list packages in" % ROOT_DIR,
    )
    npgroup.add_argument(
        '-p', "--prefix",
        action  = "store",
        default = ROOT_DIR,
        help    = "full path to Anaconda environment to list packages in (default: %s)" % ROOT_DIR,
    )
    p.set_defaults(func=execute)


def execute(args):
    conda = anaconda()

    if args.name:
        prefix = join(ROOT_DIR, 'envs', args.name)
    else:
        prefix = abspath(expanduser(args.prefix))

    env = conda.lookup_environment(prefix)

    print 'packages and versions in environment at %s:' % env.prefix

    for pkg in sort_packages_by_name(env.activated):
        print '%-25s %s' % (pkg.name, pkg.version)

