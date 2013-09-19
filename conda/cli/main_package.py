# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from __future__ import print_function, division, absolute_import

from conda.cli import common


descr = "Low-level conda package utility. (ADVANCED)"


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser('package', description=descr, help=descr)

    common.add_parser_prefix(p)
    p.add_argument(
        '-c', "--check",
        action  = "store_true",
        help    = "check (validate) the given conda packages (PATH) and exit",
    )
    p.add_argument(
        '-w', "--which",
        action = "store_true",
        help = "given some PATH print which conda package the file came from",
    )
    p.add_argument(
        '-r', "--reset",
        action  = "store_true",
        help    = "remove all untracked files and exit",
    )
    p.add_argument(
        '-u', "--untracked",
        action  = "store_true",
        help    = "display all untracked files and exit",
    )
    p.add_argument(
        "--share",
        action  = "store_true",
        help = 'Create a "share package"',
    )
    p.add_argument(
        "--pkg-name",
        action  = "store",
        default = "unknown",
        help    = "package name of the created package",
    )
    p.add_argument(
        "--pkg-version",
        action  = "store",
        default = "0.0",
        help    = "package version of the created package",
    )
    p.add_argument(
        "--pkg-build",
        action  = "store",
        default = 0,
        help    = "package build number of the created package",
    )
    p.add_argument(
        'path',
        metavar = 'PATH',
        action = "store",
        nargs = '*',
    )
    p.set_defaults(func=execute)


def execute(args, parser):
    import sys
    from os.path import basename

    from conda.misc import untracked
    from conda.builder.packup import make_tarbz2, remove


    prefix = common.get_prefix(args)

    if args.check:
        from conda.builder.tarcheck import check_all

        for path in args.path:
            try:
                check_all(path)
                print('%s OK' % basename(path))
            except Exception as e:
                print(e)
                print('%s FAILED' % basename(path))
        return

    if args.which:
        from conda.builder.packup import which_package

        for path in args.path:
            for dist in  which_package(path):
                print('%-50s  %s' % (path, dist))
        return

    if args.path:
        sys.exit("Error: no positional arguments expected.")

    print('# prefix:', prefix)

    if args.reset:
        remove(prefix, untracked(prefix))
        return

    if args.untracked:
        files = sorted(untracked(prefix))
        print('# untracked files: %d' % len(files))
        for fn in files:
            print(fn)
        return

    if args.share:
        from conda.builder.share import create_bundle

        path, warnings = create_bundle(prefix)
        for w in warnings:
            print("Warning:", w)
        print(path)
        return

    make_tarbz2(prefix,
                name = args.pkg_name,
                version = args.pkg_version,
                build_number = int(args.pkg_build))
