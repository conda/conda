# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

import common


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
        'regex',
        action  = "store",
        nargs   = "?",
        help    = "list only packages matching this regular expression",
    )
    p.set_defaults(func=execute)


def execute(args, parser):
    import re
    import conda.install as install


    prefix = common.get_prefix(args)

    if args.regex:
        pat = re.compile(args.regex, re.I)
    else:
        pat = None

    if not args.canonical:
        print '# packages in environment at %s:' % prefix
        print '#'

    for dist in sorted(install.linked(prefix)):
        name = dist.rsplit('-', 2)[0]
        if pat and pat.search(name) is None:
            continue
        if args.canonical:
            print dist
            continue
        try:
            info = install.get_meta(dist, prefix)
            features = set(info.get('features', '').split())
            print '%-25s %-15s %15s  %s' % (info['name'],
                                            info['version'],
                                            info['build'],
                                            common.disp_features(features))
        except: # IOError, KeyError, ValueError
            print '%-25s %-15s %15s' % tuple(dist.rsplit('-', 2))
