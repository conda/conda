
from optparse import OptionParser
from os import listdir
from os.path import join
from shutil import rmtree

def main_remove(args, conda, display_help=False):
    p = OptionParser(
        usage       = "usage: conda remove [options] [packages]",
        description = "Remove packages from local availability."
    )
    p.add_option(
        '-d', "--dry-run",
        action  = "store_true",
        default = False,
        help    = "display packages to be modified, without actually executing",
    )
    p.add_option(
        "--no-confirm",
        action  = "store_true",
        default = False,
        help    = "activate without confirmation",
    )

    if display_help:
        p.print_help()
        return

    opts, args = p.parse_args(args)

    if len(args) == 0:
        p.error('too few arguments')

    if opts.dry_run and opts.quiet:
        p.error('--dry-run and --quiet are mutually exclusive')

    to_remove = []
    for fn in listdir(conda.packages_dir):
        if fn in args:
            to_remove.append(fn)

    if not to_remove:
        if not opts.quiet:
            print 'No packages found to remove, nothing to do'
        return

    print "    The following packages were found and will be removed (this action may break dependencies in Anaconda environments):"
    print
    for pkg_name in to_remove:
        print "         %s" % pkg_name
    print

    if opts.dry_run: return

    if opts.no_confirm:
        proceed = raw_input("Proceed (y/n)? ")
        if proceed.lower() not in ['y', 'yes']: return

    for pkg_name in to_remove:
        rmtree(join(conda.packages_dir, pkg_name))


