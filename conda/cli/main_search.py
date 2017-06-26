# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from ..base.context import context
from conda.core.index import get_channel_priority_map
from conda.resolve import dashlist
from ..exceptions import PackageNotFoundError, ResolvePackageNotFound
from argparse import SUPPRESS

from conda import iteritems
from .conda_argparse import (add_parser_channels, add_parser_insecure, add_parser_json,
                             add_parser_known, add_parser_offline, add_parser_prefix,
                             add_parser_use_index_cache, add_parser_use_local)
from ..cli.common import stdout_json
import json
from ..common.io import spinner
from ..compat import itervalues
import sys

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
    )
    add_parser_offline(p)
    add_parser_channels(p)
    add_parser_json(p)
    add_parser_use_local(p)
    add_parser_insecure(p)
    p.set_defaults(func=execute)


def execute(args, parser):

    try:
        execute_search(args, parser)
    except ResolvePackageNotFound as e:
        pkg = []
        pkg.append(e.bad_deps)
        pkg = dashlist(pkg)
        index_args = {
        'use_cache': args.use_index_cache,
        'channel_urls': context.channels,
        'unknown': args.unknown,
        'prepend': not args.override_channels,
        'use_local': args.use_local
        }

        channel_priority_map = get_channel_priority_map(
            channel_urls=index_args['channel_urls'],
            prepend=index_args['prepend'],
            platform=None,
            use_local=index_args['use_local'],
        )

        channels_urls = tuple(channel_priority_map)

        raise PackageNotFoundError(pkg, channels_urls)


def execute_search(args, parser):
    import re
    from .common import (arg2spec, ensure_override_channels_requires_channel,
                         ensure_use_local)
    from ..core.index import get_index
    from ..models.match_spec import MatchSpec
    from ..base.context import context

    if args.reverse_dependency:
        if not args.regex:
            parser.error("--reverse-dependency requires at least one package name")
        if args.spec:
            parser.error("--reverse-dependency does not work with --spec")

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
                from ..exceptions import CommandArgumentError
                raise CommandArgumentError("Failed to compile regex pattern for "
                                           "search: %(regex)s\n"
                                           "regex error: %(regex_error)s",
                                           regex=regex, regex_error=repr(e))

    platform = args.platform or ''
    if platform and platform != context.subdir:
        args.unknown = False
    ensure_use_local(args)
    ensure_override_channels_requires_channel(args, dashc=False)

    with spinner("Loading channels", not context.verbosity and not context.quiet,
             context.json):

        index = get_index(channel_urls=context.channels, prepend=not args.override_channels,
                          platform=args.platform, use_local=args.use_local,
                          use_cache=args.use_index_cache, prefix=None,
                          unknown=args.unknown)

    spec = MatchSpec(args.regex)
    matches = {record for record in itervalues(index) if spec.match(record)}
    matches = sorted(matches, key=lambda rec: (rec.name, rec.version, rec.build))

    if not matches:
        raise ResolvePackageNotFound(args.regex)

    if context.json:
        stdout_json(matches)

    else:
        builder = []
        for record in matches:
            builder.append('%-25s  %-15s %15s  %-15s' % (
                record.name,
                record.version,
                record.build,
                record.schannel,
            ))
        sys.stdout.write('\n'.join(builder))
        sys.stdout.write('\n')
