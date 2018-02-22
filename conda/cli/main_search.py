# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from collections import defaultdict

from .install import calculate_channel_urls
from ..base.context import context
from ..cli.common import stdout_json
from ..common.io import Spinner
from ..compat import text_type
from ..core.envs_manager import query_all_prefixes
from ..core.subdir_data import SubdirData
from ..models.records import PackageRecord
from ..models.match_spec import MatchSpec
from ..models.version import VersionOrder
from ..resolve import dashlist
from ..utils import human_bytes


def execute(args, parser):
    spec = MatchSpec(args.match_spec)
    if spec.get_exact_value('subdir'):
        subdirs = spec.get_exact_value('subdir'),
    elif args.platform:
        subdirs = args.platform,
    else:
        subdirs = context.subdirs

    if args.envs:
        with Spinner("Searching environments for %s" % spec,
                     not context.verbosity and not context.quiet,
                     context.json):
            prefix_matches = query_all_prefixes(spec)
            ordered_result = tuple({
                'location': prefix,
                'package_records': tuple(sorted(
                    (PackageRecord.from_objects(prefix_rec) for prefix_rec in prefix_recs),
                    key=lambda prec: prec._pkey
                )),
            } for prefix, prefix_recs in prefix_matches)
        if context.json:
            stdout_json(ordered_result)
        else:
            builder = ['# %-13s %15s %15s  %-20s %-20s' % (
                "Name",
                "Version",
                "Build",
                "Channel",
                "Location",
            )]
            for pkg_group in ordered_result:
                for prec in pkg_group['package_records']:
                    builder.append('%-15s %15s %15s  %-20s %-20s' % (
                        prec.name,
                        prec.version,
                        prec.build,
                        prec.channel.name,
                        pkg_group['location'],
                    ))
            print('\n'.join(builder))
        return 0

    with Spinner("Loading channels", not context.verbosity and not context.quiet, context.json):
        spec_channel = spec.get_exact_value('channel')
        channel_urls = (spec_channel,) if spec_channel else context.channels

        matches = sorted(SubdirData.query_all(spec, channel_urls, subdirs),
                         key=lambda rec: (rec.name, VersionOrder(rec.version), rec.build))

    if not matches:
        channels_urls = tuple(calculate_channel_urls(
            channel_urls=context.channels,
            prepend=not args.override_channels,
            platform=subdirs[0],
            use_local=args.use_local,
        ))
        from ..exceptions import PackagesNotFoundError
        raise PackagesNotFoundError((text_type(spec),), channels_urls)

    if context.json:
        json_obj = defaultdict(list)
        for match in matches:
            json_obj[match.name].append(match)
        stdout_json(json_obj)

    elif args.info:
        for record in matches:
            pretty_record(record)

    else:
        builder = ['# %-13s %15s %15s  %-20s' % (
            "Name",
            "Version",
            "Build",
            "Channel",
        )]
        for record in matches:
            builder.append('%-15s %15s %15s  %-20s' % (
                record.name,
                record.version,
                record.build,
                record.channel.name,
            ))
        print('\n'.join(builder))


def pretty_record(record):
    def push_line(display_name, attr_name):
        value = getattr(record, attr_name, None)
        if value is not None:
            builder.append("%-12s: %s" % (display_name, value))

    builder = []
    builder.append(record.name + " " + record.version + " " + record.build)
    builder.append('-'*len(builder[0]))

    push_line("file name", "fn")
    push_line("name", "name")
    push_line("version", "version")
    push_line("build string", "build")
    push_line("build number", "build_number")
    builder.append("%-12s: %s" % ("size", human_bytes(record.size)))
    push_line("arch", "arch")
    push_line("constrains", "constrains")
    push_line("platform", "platform")
    push_line("license", "license")
    push_line("subdir", "subdir")
    push_line("url", "url")
    push_line("md5", "md5")
    builder.append("%-12s: %s" % ("dependencies", dashlist(record.depends)))
    builder.append('\n')
    print('\n'.join(builder))
