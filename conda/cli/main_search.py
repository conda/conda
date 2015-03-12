# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from __future__ import print_function, division, absolute_import

from conda.cli import common
from conda.misc import make_icon_url
from conda.resolve import NoPackagesFound
from argparse import RawDescriptionHelpFormatter
from conda import config

descr = """Search for packages and display their information. The input is a
regular expression.  To perform a search with a search string that starts with
a -, separate the search from the options with --, like 'conda search -- -h'."""
example = '''
examples:
    conda search -p ~/anaconda/envs/myenv/ scipy

'''

class Platforms(common.Completer):
    """
    Tab completion for platforms

    There is no limitation on the platform string, except by what is in the
    repo, but we want to tab complete the most common ones.
    """
    def _get_items(self):
        return ['win-32', 'win-64', 'osx-64', 'linux-32', 'linux-64']

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
    p.add_argument(
        '-f', "--full-name",
        action = "store_true",
        help = "only search for full name, ie. ^<regex>$",
    )
    p.add_argument(
        "--names-only",
        action  = "store_true",
        help    = "output only package names",
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
        "--spec",
        action  = "store_true",
        help    = "Treat regex argument as a package specification instead "
                  "(package_name[=version[=build]])",
    )
    p.add_argument(
        'regex',
        metavar = 'regex',
        action  = "store",
        nargs   = "?",
        help    = "package specification or regular expression to search for "
                  "(default: display all packages)",
    ).completer = common.Packages
    common.add_parser_offline(p)
    common.add_parser_channels(p)
    common.add_parser_json(p)
    common.add_parser_use_local(p)
    p.set_defaults(func=execute)

def execute(args, parser):
    try:
        execute_search(args, parser)
    except NoPackagesFound as e:
        common.exception_and_exit(e, json=args.json)

def execute_search(args, parser):
    import re
    from conda.resolve import MatchSpec, Resolve

    pat = None
    ms = None
    if args.regex:
        if args.spec:
            ms = MatchSpec(' '.join(args.regex.split('=')))
        else:
            regex = args.regex
            if args.full_name:
                regex = r'^%s$' % regex
            try:
                pat = re.compile(regex, re.I)
            except re.error as e:
                common.error_and_exit(
                    "'%s' is not a valid regex pattern (exception: %s)" %
                    (regex, e),
                    json=args.json,
                    error_type="ValueError")

    prefix = common.get_prefix(args)

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
    common.ensure_override_channels_requires_channel(args, dashc=False,
                                                     json=args.json)
    channel_urls = args.channel or ()
    if args.use_local:
        from conda.fetch import fetch_index
        from conda.utils import url_path
        try:
            from conda_build.config import croot
        except ImportError:
            common.error_and_exit("you need to have 'conda-build >= 1.7.1' installed"
                                  " to use the --use-local option",
                                  json=args.json,
                                  error_type="RuntimeError")
        # remove the cache such that a refetch is made,
        # this is necessary because we add the local build repo URL
        fetch_index.cache = {}
        index = common.get_index_trap(channel_urls=[url_path(croot)] + list(channel_urls),
                                      prepend=not args.override_channels,
                                      use_cache=args.use_index_cache,
                                      unknown=args.unknown,
                                      json=args.json, platform=args.platform, offline=args.offline)
    else:
        index = common.get_index_trap(channel_urls=channel_urls, prepend=not
                                      args.override_channels, platform=args.platform,
                                      use_cache=args.use_index_cache,
                                      unknown=args.unknown, json=args.json, offline=args.offline)

    r = Resolve(index)

    if args.canonical:
        json = []
    else:
        json = {}

    for name in sorted(r.groups):
        disp_name = name
        if pat and pat.search(name) is None:
            continue
        if ms and name != ms.name:
            continue

        if args.names_only:
            print(name)
            continue

        if ms:
            ms_name = ms
        else:
            ms_name = MatchSpec(name)

        if not args.canonical:
            json[name] = []

        if args.outdated:
            vers_inst = [dist.rsplit('-', 2)[1] for dist in linked
                         if dist.rsplit('-', 2)[0] == name]
            if not vers_inst:
                continue
            assert len(vers_inst) == 1, name
            pkgs = sorted(r.get_pkgs(ms_name))
            if not pkgs:
                continue
            latest = pkgs[-1]
            if latest.version == vers_inst[0]:
                continue

        for pkg in sorted(r.get_pkgs(ms_name)):
            dist = pkg.fn[:-8]
            if args.canonical:
                if not args.json:
                    print(dist)
                else:
                    json.append(dist)
                continue
            if platform and platform != config.subdir:
                inst = ' '
            elif dist in linked:
                inst = '*'
            elif dist in extracted:
                inst = '.'
            else:
                inst = ' '

            if not args.json:
                print('%-25s %s  %-15s %15s  %-15s %s' % (
                    disp_name, inst,
                    pkg.version,
                    pkg.build,
                    config.canonical_channel_name(pkg.channel),
                    common.disp_features(r.features(pkg.fn)),
                    ))
                disp_name = ''
            else:
                data = {}
                data.update(pkg.info)
                data.update({
                    'fn': pkg.fn,
                    'installed': inst == '*',
                    'extracted': inst in '*.',
                    'version': pkg.version,
                    'build': pkg.build,
                    'build_number': pkg.build_number,
                    'channel': config.canonical_channel_name(pkg.channel),
                    'full_channel': pkg.channel,
                    'features': list(r.features(pkg.fn)),
                    'license': pkg.info.get('license'),
                    'size': pkg.info.get('size'),
                    'depends': pkg.info.get('depends'),
                    'type': pkg.info.get('type')
                })

                if data['type'] == 'app':
                    data['icon'] = make_icon_url(pkg.info)
                json[name].append(data)

    if args.json:
        common.stdout_json(json)
