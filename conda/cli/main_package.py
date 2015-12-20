# (c) Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from __future__ import print_function, division, absolute_import

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
        '-u', "--untracked",
        action="store_true",
        help="Display all untracked files and exit.",
    )
    p.set_defaults(func=execute)


def execute(args, parser):
    from conda.misc import untracked, which_package

    if args.which:
        for path in args.which:
            for dist in which_package(path):
                print('%-50s  %s' % (path, dist))
        return

    prefix = common.get_prefix(args)
    print('# prefix:', prefix)

    if args.untracked:
        files = sorted(untracked(prefix))
        print('# untracked files: %d' % len(files))
        for fn in files:
            print(fn)
        return

    print('Warning: no option specified')
