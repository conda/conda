# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from __future__ import print_function, division, absolute_import

from conda.cli import common
from argparse import RawDescriptionHelpFormatter


descr = "Search for packages and display their information."
example = '''
examples:
    conda search -p ~/anaconda/envs/myenv/ scipy

'''

def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'search',
        formatter_class = RawDescriptionHelpFormatter,
        description = descr,
        help = descr,
        epilog = example,
    )
    common.add_parser_prefix(p)
    p.add_argument(
        '-c', "--canonical",
        action  = "store_true",
        help    = "output canonical names of packages only",
    )
    p.add_argument(
        '-v', "--verbose",
        action  = "store_true",
        help    = "Show available packages as blocks of data",
    )
    p.add_argument(
        'regex',
        action  = "store",
        nargs   = "?",
        help    = "package specification or regular expression to search for "
                  "(default: display all packages)",
    )
    common.add_parser_channels(p, dashc=False)
    p.set_defaults(func=execute)


def execute(args, parser):
    import re

    import conda.install as install
    from conda.api import get_index
    from conda.resolve import MatchSpec, Resolve


    if args.regex:
        pat = re.compile(args.regex, re.I)
    else:
        pat = None

    prefix = common.get_prefix(args)
    if not args.canonical:
        linked = install.linked(prefix)

    common.ensure_override_channels_requires_channel(args, dashc=False)
    channel_urls = args.channel or ()
    index = get_index(channel_urls=channel_urls, prepend=not
        args.override_channels)

    r = Resolve(index)
    for name in sorted(r.groups):
        disp_name = name
        if pat and pat.search(name) is None:
            continue
        for pkg in sorted(r.get_pkgs(MatchSpec(name))):
            dist = pkg.fn[:-8]
            if args.canonical:
                print(dist)
                continue
            inst = '*' if dist in linked else ' '
            print('%-25s %s  %-15s %15s  %s' % (
                disp_name, inst,
                pkg.version,
                r.index[pkg.fn]['build'],
                common.disp_features(r.features(pkg.fn))) )
            disp_name = ''
