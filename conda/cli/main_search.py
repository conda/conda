# (c) 2012 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

import re
from argparse import RawDescriptionHelpFormatter

from conda.anaconda import Anaconda
from conda.constraints import Satisfies
from conda.package import sort_packages_by_name
from conda.package_spec import PackageSpec
from utils import add_parser_prefix, get_prefix


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'search',
        formatter_class = RawDescriptionHelpFormatter,
        description = "Search for packages and display their information.",
        help        = "Search for packages and display their information.",
        epilog      = activate_example,
    )
    add_parser_prefix(p)
    p.add_argument(
        "--all",
        action  = "store_true",
        help    = "show all results compatible with any environment",
    )
    p.add_argument(
        '-c', "--canonical",
        action  = "store_true",
        default = False,
        help    = "output canonical names of packages only",
    )
    p.add_argument(
        '-s', "--show-requires",
        action  = "store_true",
        default = False,
        help    = "also display package requirements",
    )
    p.add_argument(
        '-v', "--verbose",
        action  = "store_true",
        default = False,
        help    = "Show available packages as blocks of data",
    )
    p.add_argument(
        'search_expression',
        action  = "store",
        nargs   = "?",
        help    = "package specification or regular expression to search for "
                  "(default: display all packages)",
    )
    p.set_defaults(func=execute)


def execute(args, parser):
    conda = Anaconda()

    if args.search_expression is None:
        pkgs = sort_packages_by_name(conda.index.pkgs)

    elif args.search_expression in conda.index.package_names:
        pkgs = conda.index.lookup_from_name(args.search_expression)

    else:
        spec = PackageSpec(args.search_expression)
        if spec.version:
           pkgs = conda.index.find_matches(
                Satisfies(spec),
                conda.index.lookup_from_name(spec.name)
            )
        else:
            try:
                pkg_names = set()
                pat = re.compile(args.search_expression)
            except:
                raise RuntimeError("Could not understand search "
                                   "expression '%s'" % args.search_expression)
            pkg_names = set()
            for name in conda.index.package_names:
                if pat.search(name):
                    pkg_names.add(name)
            pkgs = set()
            for name in pkg_names:
                pkgs |= conda.index.lookup_from_name(name)

    if args.all:
        compat_string = ''
    else:
        prefix = get_prefix(args)
        env = conda.lookup_environment(prefix)
        pkgs = conda.index.find_matches(env.requirements, pkgs)
        compat_string = ' compatible with environment %s' % prefix

    if args.canonical:
        for pkg in pkgs:
            print pkg.canonical_name
        return

    if len(pkgs) == 0:
        print "No matches found for '%s'%s" % (args.search_expression,
                                               compat_string)
        return

    if len(pkgs) == 1:
        print "One match found%s:" % compat_string
    else:
        print "%d matches found%s:" % (len(pkgs), compat_string)

    print
    print 'Packages with available versions and build strings:'


    if args.verbose:
        for pkg in pkgs:
            print
            pkg.print_info(args.show_requires)

    else:
        print
        current_name = ''
        for pkg in sorted(pkgs):
            if pkg.name != current_name:
                current_name = pkg.name
                print "%-25s %-15s %15s" % (current_name, pkg.version, pkg.build)
            else:
                print "%-25s %-15s %15s" % (" ", pkg.version, pkg.build)


activate_example = '''
examples:
    conda search -p ~/anaconda/envs/myenv/ scipy

'''






