
from os.path import abspath, expanduser
import re

from anaconda import anaconda
from constraints import all_of, build_target, satisfies
from package import sort_packages_by_name
from requirement import requirement


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'search',
        description = "Search for packages and display their information.",
        help        = "Search for packages and display their information.",
    )
    p.add_argument(
        '-p', "--prefix",
        action  = "store",
        default = None,
        help    = "only show results compatible with Anaconda environment at specified prefix location",
    )
    p.add_argument(
        '-s', "--show-requires",
        action  = "store_true",
        default = False,
        help    = "also display package requirements",
    )
    p.add_argument(
        'search_expression',
        action  = "store",
        nargs   = "?",
        metavar = 'package_name',
        help    = "package specification or regular expression to search for (default: display all packages)",

    )
    p.set_defaults(func=execute)


def execute(args):
    conda = anaconda()

    if not args.search_expression:
        for pkg in sort_packages_by_name(conda.index.pkgs):
            print
            pkg.print_info(args.show_requires)
        print
        return

    if args.search_expression in conda.index.package_names:
        pkgs = conda.index.find_matches(
            build_target(conda.target),
            conda.index.lookup_from_name(args.search_expression)
        )

    else:
        try:
           req = requirement(args.search_expression)
           pkgs = conda.index.find_matches(
                all_of(
                    satisfies(req), build_target(conda.target)
                ),
                conda.index.lookup_from_name(req.name)
            )
        except:
            try:
                pkg_names = set()
                pat = re.compile(args.search_expression)
            except:
                raise RuntimeError("Could not understand search expression '%s'" % args.search_expression)
            pkg_names = set()
            for name in conda.index.package_names:
                if pat.search(name):
                    pkg_names.add(name)
            pkgs = set()
            for name in pkg_names:
                pkgs |= conda.index.find_matches(
                    build_target(conda.target),
                    conda.index.lookup_from_name(name)
                )

    if args.prefix:
        prefix = abspath(expanduser(args.prefix))
        env = conda.lookup_environment(prefix)
        pkgs = conda.index.find_matches(env.requirements, pkgs)
        compat_string = ' compatible with environment %s' % args.prefix
    else:
        compat_string = ''

    if len(pkgs) == 0:
        print "No matches found for '%s'%s" % (args.search_expression, compat_string)
        return

    if len(pkgs) == 1:
        print "One match found%s:" % compat_string
    else:
        print "%d matches found%s:" % (len(pkgs), compat_string)

    for pkg in pkgs:
        print
        pkg.print_info(args.show_requires)
    print
