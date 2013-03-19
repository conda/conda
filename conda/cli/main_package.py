# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from os.path import basename

from conda.builder.packup import make_tarbz2, untracked, remove
from utils import add_parser_prefix, get_prefix

descr = "Create a conda package in an environment. (ADVANCED)"


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser('package', description=descr, help=descr)

    add_parser_prefix(p)

    p.add_argument(
        '-c', "--check",
        action  = "store",
        help    = "check (validate) the given tar package and exit",
        metavar = 'PATH',
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
    p.set_defaults(func=execute)


def execute(args, parser):
    prefix = get_prefix(args)

    if args.check:
        from conda.builder.tarcheck import check_all

        try:
            check_all(args.check)
            print '%s OK' % basename(args.check)
        except Exception as e:
            print e
            print '%s FAILED' % basename(args.check)
        return

    print 'prefix:', prefix

    if args.reset:
        remove(prefix, untracked(prefix))
        return

    if args.untracked:
        for fn in sorted(untracked(prefix)):
            print fn
        return

    make_tarbz2(prefix,
                name = args.pkg_name,
                version = args.pkg_version,
                build_number = int(args.pkg_build))
