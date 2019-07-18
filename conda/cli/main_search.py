# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import absolute_import, division, print_function, unicode_literals

from collections import defaultdict
from datetime import datetime

from .._vendor.boltons.timeutils import UTC
from ..base.context import context
from ..cli.common import stdout_json
from ..common.compat import text_type
from ..common.io import Spinner
from ..core.envs_manager import query_all_prefixes
from ..core.index import calculate_channel_urls
from ..core.subdir_data import SubdirData
from ..models.match_spec import MatchSpec
from ..models.records import PackageRecord
from ..models.version import VersionOrder
from ..common.io import dashlist
from ..utils import human_bytes


def execute(args, parser):
    spec = MatchSpec(args.match_spec)
    if spec.get_exact_value('subdir'):
        subdirs = spec.get_exact_value('subdir'),
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
        elif args.info:
            for pkg_group in ordered_result:
                for prec in pkg_group['package_records']:
                    pretty_record(prec)
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
    if not matches and spec.get_exact_value("name"):
        flex_spec = MatchSpec(spec, name="*%s*" % spec.name)
        if not context.json:
            print("No match found for: %s. Search: %s" % (spec, flex_spec))
        matches = sorted(SubdirData.query_all(flex_spec, channel_urls, subdirs),
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
        builder = ['# %-18s %15s %15s  %-20s' % (
            "Name",
            "Version",
            "Build",
            "Channel",
        )]
        for record in matches:
            builder.append('%-20s %15s %15s  %-20s' % (
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
    push_line("build", "build")
    push_line("build number", "build_number")
    builder.append("%-12s: %s" % ("size", human_bytes(record.size)))
    push_line("license", "license")
    push_line("subdir", "subdir")
    push_line("url", "url")
    push_line("md5", "md5")
    if record.timestamp:
        date_str = datetime.fromtimestamp(record.timestamp, UTC).strftime('%Y-%m-%d %H:%M:%S %Z')
        builder.append("%-12s: %s" % ("timestamp", date_str))
    if record.track_features:
        builder.append("%-12s: %s" % ("track_features", dashlist(record.track_features)))
    if record.constrains:
        builder.append("%-12s: %s" % ("constraints", dashlist(record.constrains)))
    builder.append(
        "%-12s: %s" % ("dependencies", dashlist(record.depends) if record.depends else "[]")
    )
    builder.append('\n')
    print('\n'.join(builder))
