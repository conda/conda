# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import sys
from argparse import SUPPRESS
from collections import defaultdict

from conda.core.index import get_channel_priority_map
from .conda_argparse import (add_parser_channels, add_parser_insecure, add_parser_json,
                             add_parser_known, add_parser_offline, add_parser_prefix,
                             add_parser_use_index_cache, add_parser_use_local)
from ..base.context import context
from ..cli.common import stdout_json
from ..common.io import spinner
from ..compat import itervalues
from ..exceptions import ResolvePackageNotFound, PackagesNotFoundError

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
        help=SUPPRESS,
    )
    p.add_argument(
        '-f', "--full-name",
        action="store_true",
        help=SUPPRESS,
    )
    p.add_argument(
        "--names-only",
        action="store_true",
        help=SUPPRESS,
    )
    add_parser_known(p)
    add_parser_use_index_cache(p)
    p.add_argument(
        '-o', "--outdated",
        action="store_true",
        help=SUPPRESS,
    )
    p.add_argument(
        '--platform',
        action='store',
        dest='platform',
        help="""Search the given platform. Should be formatted like 'osx-64', 'linux-32',
        'win-64', and so on. The default is to search the current platform.""",
        default=None,
    )
    p.add_argument(
        'spec',
        default='*',
        nargs='?',
    )
    # p.add_argument(
    #     "--spec",
    #     action="store_true",
    #     help=SUPPRESS,
    # )
    p.add_argument(
        "--reverse-dependency",
        action="store_true",
        help="""Perform a reverse dependency search. When using this flag, the --full-name
flag is recommended. Use 'conda info package' to see the dependencies of a
package.""",
    )
    # p.add_argument(
    #     'regex',
    #     metavar='regex',
    #     action="store",
    #     nargs="?",
    #     help="""Package specification or Python regular expression to search for (default: display
    #     all packages).""",
    # )
    add_parser_offline(p)
    add_parser_channels(p)
    add_parser_json(p)
    add_parser_use_local(p)
    add_parser_insecure(p)
    p.set_defaults(func=execute)


def execute(args, parser):
    from .common import (ensure_override_channels_requires_channel,
                         ensure_use_local)
    from ..core.index import get_index
    from ..models.match_spec import MatchSpec
    from ..models.version import VersionOrder
    from ..base.context import context

    platform = args.platform or ''
    if platform and platform != context.subdir:
        args.unknown = False
    ensure_use_local(args)
    ensure_override_channels_requires_channel(args, dashc=False)

    with spinner("Loading channels", not context.verbosity and not context.quiet, context.json):
        index = get_index(channel_urls=context.channels, prepend=not args.override_channels,
                          platform=args.platform, use_local=args.use_local,
                          use_cache=args.use_index_cache, prefix=None,
                          unknown=args.unknown)

    spec = MatchSpec(args.spec)
    matches = {record for record in itervalues(index) if spec.match(record)}
    matches = sorted(matches, key=lambda rec: (rec.name, VersionOrder(rec.version), rec.build))

    if not matches:
        channel_priority_map = get_channel_priority_map(
            channel_urls=context.channels,
            prepend=not args.override_channels,
            platform=None,
            use_local=args.use_local,
        )
        channels_urls = tuple(channel_priority_map)
        from ..models.match_spec import MatchSpec
        raise PackagesNotFoundError((MatchSpec(args.spec),), channels_urls)

    if context.json:
        json_obj = defaultdict(list)
        for match in matches:
            json_obj[match.name].append(match)
        stdout_json(json_obj)

    else:

        builder = ['%-25s  %-15s %15s  %-15s' % (
            "Name",
            "Version",
            "Build",
            "Channel",
        )]
        for record in matches:
            builder.append('%-25s  %-15s %15s  %-15s' % (
                record.name,
                record.version,
                record.build,
                record.schannel,
            ))
        sys.stdout.write('\n'.join(builder))
        sys.stdout.write('\n')
