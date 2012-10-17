
from difflib import get_close_matches
from optparse import OptionParser
from os.path import abspath, expanduser

from anaconda import anaconda
from constraints import all_of, build_target, satisfies
from requirement import requirement


def main_search(args, display_help=False):
    p = OptionParser(
        usage       = "usage: conda search <package>",
        description = "Display information about a specified package."
    )
    p.add_option(
        '-r', "--show-requires",
        action  = "store_true",
        default = False,
        help    = "also display package requirements, default is False",
    )
    p.add_option(
        '-p', "--prefix",
        action  = "store",
        default = None,
        help    = "only show results compatible with Anaconda environment at prefix locations",
    )

    if display_help:
        p.print_help()
        return

    opts, args = p.parse_args(args)

    if len(args) == 0:
        p.error('too few arguments')

    if len(args) > 1:
        p.error('too many arguments')

    conda = anaconda()

    pkg_name = args[0]

    if pkg_name not in conda.index.package_names:
        print "Unknown package '%s'." % pkg_name,
        close = get_close_matches(args[0], conda.index.package_names)
        if close:
            print 'Did you mean one of these?'
            print
            for s in close:
                print '    %s' % s
        print
        return

    try:
        req = requirement(pkg_name)
        pkgs = conda.index.find_matches(
            all_of(
                satisfies(req), build_target(conda.target)
            ),
            conda.index.lookup_from_name(req.name)
        )
    except RuntimeError:
        pkgs = conda.index.find_matches(
            build_target(conda.target),
            conda.index.lookup_from_name(pkg_name)
        )

    if opts.prefix:
        prefix = abspath(expanduser(opts.prefix))
        env = conda.lookup_environment(prefix)
        pkgs = conda.index.find_matches(env.requirements, pkgs)

    if opts.prefix:
        compat_string = ' compatible with environment %s' % opts.prefix
    else:
        compat_string = ''

    if len(pkgs) == 0:
        print "No matches found for '%s'%s" % (pkg_name, compat_string)
        return

    if len(pkgs) == 1:
        print "One match found%s:" % compat_string
    else:
        print "%d matches found%s:" % (len(pkgs), compat_string)

    for pkg in pkgs:
        print
        pkg.print_info(opts.show_requires)
    print
