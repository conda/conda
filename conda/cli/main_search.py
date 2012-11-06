
from argparse import ArgumentDefaultsHelpFormatter
from difflib import get_close_matches
from os.path import abspath, expanduser

from anaconda import anaconda
from constraints import all_of, build_target, satisfies
from package import sort_packages_by_name
from requirement import requirement


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'search',
        description = "Display information about a specified package.",
        help        = "Display information about a specified package.",
        formatter_class = ArgumentDefaultsHelpFormatter,
    )
    p.add_argument(
        '-p', "--prefix",
        action  = "store",
        default = None,
        help    = "only show results compatible with Anaconda environment at prefix locations",
    )
    p.add_argument(
        '-s', "--show-requires",
        action  = "store_true",
        default = False,
        help    = "also display package requirements",
    )
    p.add_argument(
        'pkg_name',
        action  = "store",
        nargs   = "?",
        metavar = 'package_name',
        help    = "omit to display all packages",

    )
    p.set_defaults(func=execute)


def execute(args, parser):
    conda = anaconda()

    if not args.pkg_name:
        for pkg in sort_packages_by_name(conda.index.pkgs):
            print
            pkg.print_info(args.show_requires)
        print
        return

    if args.pkg_name not in conda.index.package_names:
        print "Unknown package '%s'." % args.pkg_name,
        close = get_close_matches(args.pkg_name, conda.index.package_names)
        if close:
            print 'Did you mean one of these?'
            print
            for s in close:
                print '    %s' % s
        print
        return

    try:
        req = requirement(args.pkg_name)
        pkgs = conda.index.find_matches(
            all_of(
                satisfies(req), build_target(conda.target)
            ),
            conda.index.lookup_from_name(req.name)
        )
    except RuntimeError:
        pkgs = conda.index.find_matches(
            build_target(conda.target),
            conda.index.lookup_from_name(args.pkg_name)
        )

    if args.prefix:
        prefix = abspath(expanduser(args.prefix))
        env = conda.lookup_environment(prefix)
        pkgs = conda.index.find_matches(env.requirements, pkgs)
        compat_string = ' compatible with environment %s' % args.prefix
    else:
        compat_string = ''

    if len(pkgs) == 0:
        print "No matches found for '%s'%s" % (args.pkg_name, compat_string)
        return

    if len(pkgs) == 1:
        print "One match found%s:" % compat_string
    else:
        print "%d matches found%s:" % (len(pkgs), compat_string)

    for pkg in pkgs:
        print
        pkg.print_info(args.show_requires)
    print
