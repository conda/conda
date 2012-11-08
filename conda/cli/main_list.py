
from argparse import ArgumentDefaultsHelpFormatter
from os.path import abspath, expanduser

from anaconda import anaconda
from config import ROOT_DIR
from package import sort_packages_by_name


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'list',
        description     = "List activated packages in an Anaconda environment.",
        help            = "List activated packages in an Anaconda environment.",
        formatter_class = ArgumentDefaultsHelpFormatter,
    )
    p.add_argument(
        '-p', "--prefix",
        action  = "store",
        default = ROOT_DIR,
        help    = "list packages in the specified Anaconda environment",
    )
    p.set_defaults(func=execute)


def execute(args, parser):
    conda = anaconda()

    prefix = abspath(expanduser(args.prefix))

    env = conda.lookup_environment(prefix)

    print 'packages and versions in environment at %s:' % env.prefix

    for pkg in sort_packages_by_name(env.activated):
        print '%-25s %s' % (pkg.name, pkg.version)

