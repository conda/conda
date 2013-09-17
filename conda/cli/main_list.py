# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from __future__ import print_function, division, absolute_import

import sys

from conda.cli import common


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'list',
        description = "List linked packages in a conda environment.",
        help        = "List linked packages in a conda environment.",
    )
    common.add_parser_prefix(p)
    p.add_argument(
        '-c', "--canonical",
        action  = "store_true",
        help    = "output canonical names of packages only",
    )
    p.add_argument(
        '-e', "--export",
        action  = "store_true",
        help    = "output requirement string only "
                  "(output may be used by conda install --file)",
    )
    p.add_argument(
        'regex',
        action  = "store",
        nargs   = "?",
        help    = "list only packages matching this regular expression",
    )
    p.set_defaults(func=execute)


def list_packages(prefix, regex=None, format='human'):
    import re
    import conda.install as install
    import os.path

    if not os.path.isdir(prefix):
        sys.exit("""\
Error: environment does not exist: %s
#
# Use 'conda create' to create an environment before listing its packages.""" % prefix)
    pat = re.compile(regex, re.I) if regex else None

    if format == 'human':
        print('# packages in environment at %s:' % prefix)
        print('#')
        res = 1

    for dist in sorted(install.linked(prefix)):
        name = dist.rsplit('-', 2)[0]
        if pat and pat.search(name) is None:
            continue
        res = 0
        if format == 'canonical':
            print(dist)
            continue
        if format == 'export':
            print('='.join(dist.rsplit('-', 2)))
            continue
        try:
            info = install.is_linked(prefix, dist)
            features = set(info.get('features', '').split())
            print('%-25s %-15s %15s  %s' % (info['name'],
                                            info['version'],
                                            info['build'],
                                            common.disp_features(features)))
        except: # IOError, KeyError, ValueError
            print('%-25s %-15s %15s' % tuple(dist.rsplit('-', 2)))

    return res


def execute(args, parser):
    prefix = common.get_prefix(args)

    if args.canonical:
        format = 'canonical'
    elif args.export:
        format = 'export'
    else:
        format = 'human'
    sys.exit(list_packages(prefix, args.regex, format=format))
