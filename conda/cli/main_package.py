# (c) Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.
from __future__ import print_function, division, absolute_import

import os
from os.path import dirname, join

from conda.cli import common


descr = "Low-level conda package utility. (EXPERIMENTAL)"


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'package',
        description=descr,
        help=descr,
    )
    common.add_parser_prefix(p)
    p.add_argument(
        '-w', "--which",
        metavar="PATH",
        nargs='+',
        action="store",
        help="Given some PATH print which conda package the file came from.",
    )
    p.add_argument(
        '-r', "--reset",
        action="store_true",
        help="Remove all untracked files and exit.",
    )
    p.add_argument(
        '-u', "--untracked",
        action="store_true",
        help="Display all untracked files and exit.",
    )
    p.add_argument(
        "--pkg-name",
        action="store",
        default="unknown",
        help="Package name of the created package.",
    )
    p.add_argument(
        "--pkg-version",
        action="store",
        default="0.0",
        help="Package version of the created package.",
    )
    p.add_argument(
        "--pkg-build",
        action="store",
        default=0,
        help="Package build number of the created package.",
    )
    p.set_defaults(func=execute)


def remove(prefix, files):
    """
    Remove files for a given prefix.
    """
    dst_dirs = set()
    for f in files:
        dst = join(prefix, f)
        dst_dirs.add(dirname(dst))
        os.unlink(dst)

    for path in sorted(dst_dirs, key=len, reverse=True):
        try:
            os.rmdir(path)
        except OSError:  # directory might not be empty
            pass


def execute(args, parser):
    from conda.misc import untracked, which_package
    from conda.packup import make_tarbz2


    prefix = common.get_prefix(args)

    if args.which:
        for path in args.which:
            for dist in which_package(path):
                print('%-50s  %s' % (path, dist))
        return

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

    make_tarbz2(prefix,
                name=args.pkg_name.lower(),
                version=args.pkg_version,
                build_number=int(args.pkg_build))
