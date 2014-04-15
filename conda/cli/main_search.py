# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from __future__ import print_function, division, absolute_import

from conda.cli import common
from argparse import RawDescriptionHelpFormatter
from conda import config

descr = """Search for packages and display their information. The input is a
regular expression.  To perform a search with a search string that starts with
a -, separate the search from the options with --, like 'conda search -- -h'."""
example = '''
examples:
    conda search -p ~/anaconda/envs/myenv/ scipy

'''

class Platforms(object):
    """
    Tab completion for platforms

    There is no limitation on the platform string, except by what is in the
    repo, but we want to tab complete the most common ones.
    """
    def __contains__(self, other):
        return True

    def __iter__(self):
        for i in ['win-32', 'win-64', 'osx-64', 'linux-32', 'linux-64']:
            yield i

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
        "--canonical",
        action  = "store_true",
        help    = "output canonical names of packages only",
    )
    common.add_parser_known(p)
    common.add_parser_use_index_cache(p)
    p.add_argument(
        '-o', "--outdated",
        action  = "store_true",
        help    = "only display installed but outdated packages",
    )
    p.add_argument(
        '-v', "--verbose",
        action  = "store_true",
        help    = "Show available packages as blocks of data",
    )
    p.add_argument(
        '--platform',
        action='store',
        dest='platform',
        help="""Search the given platform. Should be formatted like 'osx-64', 'linux-32',
        'win-64', and so on. The default is to search the current platform.""",
        choices=Platforms(),
        default=None,
        )
    p.add_argument(
        'regex',
        action  = "store",
        nargs   = "?",
        help    = "package specification or regular expression to search for "
                  "(default: display all packages)",
    )
    common.add_parser_channels(p)
    p.set_defaults(func=execute)

def execute(args, parser):
    import re

    from conda.api import get_index
    from conda.resolve import MatchSpec, Resolve

    if args.regex:
        pat = re.compile(args.regex, re.I)
    else:
        pat = None

    prefix = common.get_prefix(args)
    if not args.canonical:
        import conda.config
        import conda.install

        linked = conda.install.linked(prefix)
        extracted = set()
        for pkgs_dir in conda.config.pkgs_dirs:
            extracted.update(conda.install.extracted(pkgs_dir))

    # XXX: Make this work with more than one platform
    platform = args.platform or ''
    if platform and platform != config.subdir:
        args.unknown = False
    common.ensure_override_channels_requires_channel(args, dashc=False)
    channel_urls = args.channel or ()
    index = get_index(channel_urls=channel_urls, prepend=not
                      args.override_channels, platform=args.platform,
                      use_cache=args.use_index_cache,
                      unknown=args.unknown)

    r = Resolve(index)
    for name in sorted(r.groups):
        disp_name = name
        if pat and pat.search(name) is None:
            continue

        if args.outdated:
            vers_inst = [dist.rsplit('-', 2)[1] for dist in linked
                         if dist.rsplit('-', 2)[0] == name]
            if not vers_inst:
                continue
            assert len(vers_inst) == 1, name
            pkgs = sorted(r.get_pkgs(MatchSpec(name)))
            if not pkgs:
                continue
            latest = pkgs[-1]
            if latest.version == vers_inst[0]:
                continue

        for pkg in sorted(r.get_pkgs(MatchSpec(name))):
            dist = pkg.fn[:-8]
            if args.canonical:
                print(dist)
                continue
            if dist in linked:
                inst = '*'
            elif dist in extracted:
                inst = '.'
            else:
                inst = ' '

            print('%-25s %s  %-15s %15s  %-15s %s' % (
                disp_name, inst,
                pkg.version,
                r.index[pkg.fn]['build'],
                config.canonical_channel_name(pkg.channel),
                common.disp_features(r.features(pkg.fn)),
                ))
            disp_name = ''
