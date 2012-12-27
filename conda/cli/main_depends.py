# (c) 2012 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from argparse import RawDescriptionHelpFormatter

from conda.anaconda import Anaconda
from utils import add_parser_prefix, get_prefix


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'depends',
        formatter_class = RawDescriptionHelpFormatter,
        description = "Query Anaconda package dependencies.",
        help        = "Query Anaconda package dependencies.",
        epilog          = activate_example,
    )
    p.add_argument(
        '-m', "--max-depth",
        action  = "store",
        type    = int,
        default = 0,
        help    = "maximum depth to search dependencies, 0 searches all depths (default: 0)",
    )
    p.add_argument(
        "--all",
        action  = "store_true",
        default = False,
        help    = "return reverse dependencies compatible with any specified environment, overrides --name and --prefix",
    )
    add_parser_prefix(p)
    p.add_argument(
        '-r', "--reverse",
        action  = "store_true",
        default = False,
        help    = "generate reverse dependencies",
    )
    p.add_argument(
        '-v', "--verbose",
        action  = "store_true",
        default = False,
        help    = "display build strings on reverse dependencies",
    )
    p.add_argument(
        'pkg_names',
        action  = "store",
        metavar = 'package_name',
        nargs   = '+',
    )
    p.set_defaults(func=execute)


def execute(args):
    conda = Anaconda()

    prefix = get_prefix(args)

    env = conda.lookup_environment(prefix)

    pkgs = set()
    for pkg_name in args.pkg_names:
        pkg = env.find_activated_package(pkg_name)
        if pkg:
            pkgs.add(pkg)
        else:
            tmp = conda.index.lookup_from_name(pkg_name)
            if not tmp:
                raise RuntimeError("package name '%s' is unknown" % pkg_name)
            if args.all:
                pkgs |= conda.index.lookup_from_name(pkg_name)
            else:
                raise RuntimeError("package '%s' not installed in environment at: %s" % (pkg_name, prefix))

    if args.reverse:
        rdeps = conda.index.get_reverse_deps(pkgs, args.max_depth)

        fmt = '%s' if len(args.pkg_names) == 1 else '{%s}'

        if not args.all:
            rdeps &= env.activated

        if len(rdeps) == 0:
            print 'No packages depend on ' + fmt % ', '.join(args.pkg_names)
            return

        if args.verbose:
            names = sorted([pkg.canonical_name for pkg in rdeps])
        else:
            names = [str(pkg) for pkg in rdeps]
            names_count = dict((k, names.count(k)) for k in names)
            names = sorted(list(set(names)))

        activated = '' if args.all else 'activated '
        print 'The following %spackages depend on ' % activated + fmt % ', '.join(args.pkg_names) + ':'

    else:
        deps = conda.index.get_deps(pkgs, args.max_depth)

        if not args.all:
            deps &= env.activated

        if len(deps) == 0:
            suffix, fmt = ('es', '%s') if len(args.pkg_names) == 1 else ('', '{%s}')
            print (fmt + ' do%s not depend on any packages') % (', '.join(args.pkg_names), suffix)
            return

        if args.verbose:
            names = sorted([pkg.canonical_name for pkg in deps])
        else:
            names = [str(pkg) for pkg in deps]
            names_count = dict((k, names.count(k)) for k in names)
            names = sorted(list(set(names)))

        activated = '' if args.all else 'activated '
        suffix, fmt = ('s', '%s') if len(args.pkg_names) == 1 else ('', '{%s}')
        print (fmt + ' depend%s on the following packages:') % (', '.join(args.pkg_names), suffix)

    for name in names:
        if args.verbose or names_count[name]==1:
            print '    %s' % name
        else:
            print '    %s (%d builds)' % (name, names_count[name])

activate_example = '''
examples:
    conda depends -n myenv numpy

'''
