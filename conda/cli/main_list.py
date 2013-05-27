# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

import utils


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'list',
        description = "List linked packages in a conda environment.",
        help        = "List linked packages in a conda environment.",
    )
    utils.add_parser_prefix(p)
    p.add_argument(
        '-c', "--canonical",
        action  = "store_true",
        help    = "output canonical names of packages only",
    )
    p.add_argument(
        'search_expression',
        action  = "store",
        nargs   = "?",
        help    = "list only packages matching this regular expression",
    )
    p.set_defaults(func=execute)


def execute(args, parser):
    import re
    from conda.install import linked

    prefix = utils.get_prefix(args)
    pkgs = sorted(linked(prefix))

    matching = ""
    if args.search_expression:
        try:
            pat = re.compile(args.search_expression)
        except:
            raise RuntimeError(
                "Could not understand search expression '%s'" %
                args.search_expression)
        matching = " matching '%s'" % args.search_expression
        pkgs = [pkg for pkg in pkgs if pat.search(pkg)]

    if args.canonical:
        for pkg in pkgs:
            print pkg
        return

    if len(pkgs) == 0:
        print('no packages%s found in environment at %s:' %
              (matching, prefix))
        return

    print '# packages%s in environment at %s:' % (matching, prefix)
    print '#'
    for pkg in pkgs:
        print '%-25s %-15s %15s' % tuple(pkg.rsplit('-', 2))
