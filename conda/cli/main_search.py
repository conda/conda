# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import sys
from argparse import SUPPRESS
from collections import defaultdict

from conda.core.index import get_channel_priority_map
from .conda_argparse import (add_parser_channels, add_parser_insecure, add_parser_json,
                             add_parser_known, add_parser_offline, add_parser_prefix,
                             add_parser_use_index_cache, add_parser_use_local)
from ..cli.common import stdout_json
from ..common.io import spinner
from ..compat import itervalues, text_type
from ..exceptions import PackagesNotFoundError

descr = """Search for packages and display their information. The input is a
MatchSpec, which is a fundamentally query language for conda packages.  To perform a search with a search string that starts
with a -, separate the search from the options with --, like 'conda search -- -h'.

"""
example = '''
Examples:

Search for a specific package (but no other packages that have 'scikit-learn'
in the name):

    conda search scikit-learn

Search for packages that has 'scikit' in its name:

   conda search "*scikit*"
   conda search "scikit*"

Search for packages for 64-bit Linux (by default, packages for your current
platform are shown):

   conda search --platform linux-64
   conda search numpy --platform linux-64

Search for a specific version of a package:

   conda search numpy=1.12

Search for a package in a specific channel (e.g. conda-forge):

   conda search conda-forge::numpy
   conda search conda-forge::numpy=1.12

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
        'match_spec',
        default='*',
        nargs='?',
    )
    p.add_argument(
        "--spec",
        action="store_true",
        help=SUPPRESS,
    )
    p.add_argument(
        "--reverse-dependency",
        action="store_true",
        help="""Perform a reverse dependency search. When using this flag, the --full-name
flag is recommended. Use 'conda info package' to see the dependencies of a
package.""",
    )
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

    spec = MatchSpec(args.match_spec)
    with spinner("Loading channels", not context.verbosity and not context.quiet, context.json):
        spec_channel = spec.get_exact_value('channel')
        channel_urls = (spec_channel,) if spec_channel else context.channels
        index = get_index(channel_urls=channel_urls,
                          prepend=not args.override_channels,
                          platform=args.platform, use_local=args.use_local,
                          use_cache=args.use_index_cache, prefix=None,
                          unknown=args.unknown)

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
        raise PackagesNotFoundError((text_type(spec),), channels_urls)

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
