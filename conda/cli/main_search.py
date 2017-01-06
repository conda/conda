# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from __future__ import absolute_import, division, print_function, unicode_literals

from .common import (Completer, Packages, add_parser_channels, add_parser_json, add_parser_known,
                     add_parser_offline, add_parser_prefix, add_parser_use_index_cache,
                     add_parser_use_local, disp_features, arg2spec,
                     ensure_override_channels_requires_channel, ensure_use_local, stdout_json)
from ..api import get_index
from ..base.context import context
from ..common.compat import text_type
from ..exceptions import CommandArgumentError, PackageNotFoundError
from ..misc import make_icon_url
from ..resolve import MatchSpec, NoPackagesFoundError

descr = """Search for packages and display their information. The input is a
Python regular expression.  To perform a search with a search string that starts
with a -, separate the search from the options with --, like 'conda search -- -h'.

A * in the results means that package is installed in the current
environment. A . means that package is not installed but is cached in the pkgs
directory.
"""
example = '''
Examples:

Search for packages with 'scikit' in the name:

    conda search scikit

Search for the 'python' package (but no other packages that have 'python' in
the name):

   conda search -f python

Search for packages for 64-bit Linux (by default, packages for your current
platform are shown):

   conda search --platform linux-64
'''

class Platforms(Completer):
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
        description=descr,
        help=descr,
        epilog=example,
    )
    add_parser_prefix(p)
    p.add_argument(
        "--canonical",
        action="store_true",
        help="Output canonical names of packages only.",
    )
    p.add_argument(
        '-f', "--full-name",
        action="store_true",
        help="Only search for full name, ie. ^<regex>$.",
    )
    p.add_argument(
        "--names-only",
        action="store_true",
        help="Output only package names.",
    )
    add_parser_known(p)
    add_parser_use_index_cache(p)
    p.add_argument(
        '-o', "--outdated",
        action="store_true",
        help="Only display installed but outdated packages.",
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
        action="store_true",
        help="""Treat the regex argument as a package specification instead
        (package_name[=version[=build]]).""",
    )
    p.add_argument(
        "--reverse-dependency",
        action="store_true",
        help="""Perform a reverse dependency search. When using this flag, the --full-name
flag is recommended. Use 'conda info package' to see the dependencies of a
package.""",
    )
    p.add_argument(
        'regex',
        metavar='regex',
        action="store",
        nargs="?",
        help="""Package specification or Python regular expression to search for (default: display
        all packages).""",
    ).completer = Packages
    add_parser_offline(p)
    add_parser_channels(p)
    add_parser_json(p)
    add_parser_use_local(p)
    p.set_defaults(func=execute)

def execute(args, parser):
    try:
        execute_search(args, parser)
    except NoPackagesFoundError as e:
        raise PackageNotFoundError('', text_type(e))

def execute_search(args, parser):
    import re
    from conda.resolve import Resolve

    if args.reverse_dependency:
        if not args.regex:
            parser.error("--reverse-dependency requires at least one package name")
        if args.spec:
            parser.error("--reverse-dependency does not work with --spec")

    pat = None
    ms = None
    if args.regex:
        if args.spec:
            ms = MatchSpec(arg2spec(args.regex))
        else:
            regex = args.regex
            if args.full_name:
                regex = r'^%s$' % regex
            try:
                pat = re.compile(regex, re.I)
            except re.error as e:
                raise CommandArgumentError("Failed to compile regex pattern for "
                                           "search: %(regex)s\n"
                                           "regex error: %(regex_error)s",
                                           regex=regex, regex_error=repr(e))

    prefix = context.prefix_w_legacy_search

    from ..core.linked_data import linked as linked_data
    from ..core.package_cache import PackageCache

    linked = linked_data(prefix)
    extracted = set(pc_entry.dist.name for pc_entry in PackageCache.get_all_extracted_entries())

    # XXX: Make this work with more than one platform
    platform = args.platform or ''
    if platform and platform != context.subdir:
        args.unknown = False
    ensure_use_local(args)
    ensure_override_channels_requires_channel(args, dashc=False)
    index = get_index(channel_urls=context.channels, prepend=not args.override_channels,
                      platform=args.platform, use_local=args.use_local,
                      use_cache=args.use_index_cache, prefix=None,
                      unknown=args.unknown)

    r = Resolve(index)

    if args.canonical:
        json = []
    else:
        json = {}

    names = []
    for name in sorted(r.groups):
        if '@' in name:
            continue
        res = []
        if args.reverse_dependency:
            res = [dist for dist in r.get_dists_for_spec(name)
                   if any(pat.search(dep.name) for dep in r.ms_depends(dist))]
        elif ms is not None:
            if ms.name == name:
                res = r.get_dists_for_spec(ms)
        elif pat is None or pat.search(name):
            res = r.get_dists_for_spec(name)
        if res:
            names.append((name, res))

    for name, pkgs in names:
        disp_name = name

        if args.names_only and not args.outdated:
            print(name)
            continue

        if not args.canonical:
            json[name] = []

        if args.outdated:
            vers_inst = [dist.quad[1] for dist in linked if dist.quad[0] == name]
            if not vers_inst:
                continue
            assert len(vers_inst) == 1, name
            if not pkgs:
                continue
            latest = pkgs[-1]
            if latest.version == vers_inst[0]:
                continue
            if args.names_only:
                print(name)
                continue

        for dist in pkgs:
            index_record = r.index[dist]
            if args.canonical:
                if not context.json:
                    print(dist.dist_name)
                else:
                    json.append(dist.dist_name)
                continue
            if platform and platform != context.subdir:
                inst = ' '
            elif dist in linked:
                inst = '*'
            elif dist in extracted:
                inst = '.'
            else:
                inst = ' '

            features = r.features(dist)

            if not context.json:
                print('%-25s %s  %-15s %15s  %-15s %s' % (
                    disp_name, inst,
                    index_record.version,
                    index_record.build,
                    index_record.schannel,
                    disp_features(features),
                ))
                disp_name = ''
            else:
                data = {}
                data.update(index_record.dump())
                data.update({
                    'fn': index_record.fn,
                    'installed': inst == '*',
                    'extracted': inst in '*.',
                    'version': index_record.version,
                    'build': index_record.build,
                    'build_number': index_record.build_number,
                    'channel': index_record.schannel,
                    'full_channel': index_record.channel,
                    'features': list(features),
                    'license': index_record.get('license'),
                    'size': index_record.get('size'),
                    'depends': index_record.get('depends'),
                    'type': index_record.get('type')
                })

                if data['type'] == 'app':
                    data['icon'] = make_icon_url(index_record.info)
                json[name].append(data)

    if context.json:
        stdout_json(json)
