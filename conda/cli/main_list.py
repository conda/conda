
from optparse import OptionParser
from os.path import abspath, expanduser

from package import sort_packages_by_name

def main_list(args, conda, display_help=False):
    p = OptionParser(
        usage       = "usage: conda list [options]",
        description = "List activated packages in an Anaconda environment.",
    )
    p.add_option(
        '-p', "--prefix",
        action  = "store",
        default = conda.root_dir,
        help    = "list packages in a specified environment, defaults to %default",
    )

    if display_help:
        p.print_help()
        return

    opts, args = p.parse_args(args)
    if len(args) > 0:
        p.error('no arguments expected')

    env = conda.lookup_environment(abspath(expanduser(opts.prefix)))

    for pkg in sort_packages_by_name(env.activated):
        print '%-25s %s' % (pkg.name, pkg.version)

