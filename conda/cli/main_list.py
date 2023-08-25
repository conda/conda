# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""CLI implementation for `conda list`.

Lists all packages installed into an environment.
"""
import logging
import re
from os.path import isdir, isfile

from ..base.constants import DEFAULTS_CHANNEL_NAME, UNKNOWN_CHANNEL
from ..base.context import context
from ..core.prefix_data import PrefixData
from ..gateways.disk.test import is_conda_environment
from ..history import History
from .common import disp_features, stdout_json

log = logging.getLogger(__name__)


def print_export_header(subdir):
    print("# This file may be used to create an environment using:")
    print("# $ conda create --name <env> --file <this file>")
    print("# platform: %s" % subdir)


def get_packages(installed, regex):
    pat = re.compile(regex, re.I) if regex else None
    for prefix_rec in sorted(installed, key=lambda x: x.name.lower()):
        if pat and pat.search(prefix_rec.name) is None:
            continue
        yield prefix_rec


def list_packages(
    prefix, regex=None, format="human", reverse=False, show_channel_urls=None
):
    res = 0

    installed = sorted(
        PrefixData(prefix, pip_interop_enabled=True).iter_records(),
        key=lambda x: x.name,
    )

    packages = []
    for prec in get_packages(installed, regex) if regex else installed:
        if format == "canonical":
            packages.append(
                prec.dist_fields_dump() if context.json else prec.dist_str()
            )
            continue
        if format == "export":
            packages.append("=".join((prec.name, prec.version, prec.build)))
            continue

        features = set(prec.get("features") or ())
        disp = "%(name)-25s %(version)-15s %(build)15s" % prec
        disp += "  %s" % disp_features(features)
        schannel = prec.get("schannel")
        show_channel_urls = show_channel_urls or context.show_channel_urls
        if (
            show_channel_urls
            or show_channel_urls is None
            and schannel != DEFAULTS_CHANNEL_NAME
        ):
            disp += "  %s" % schannel

        packages.append(disp)

    if reverse:
        packages = reversed(packages)

    result = []
    if format == "human":
        result = [
            "# packages in environment at %s:" % prefix,
            "#",
            "# %-23s %-15s %15s  Channel" % ("Name", "Version", "Build"),
        ]
    result.extend(packages)

    return res, result


def print_packages(
    prefix,
    regex=None,
    format="human",
    reverse=False,
    piplist=False,
    json=False,
    show_channel_urls=None,
):
    if not isdir(prefix):
        from ..exceptions import EnvironmentLocationNotFound

        raise EnvironmentLocationNotFound(prefix)

    if not json:
        if format == "export":
            print_export_header(context.subdir)

    exitcode, output = list_packages(
        prefix,
        regex,
        format=format,
        reverse=reverse,
        show_channel_urls=show_channel_urls,
    )
    if context.json:
        stdout_json(output)

    else:
        print("\n".join(map(str, output)))

    return exitcode


def print_explicit(prefix, add_md5=False):
    if not isdir(prefix):
        from ..exceptions import EnvironmentLocationNotFound

        raise EnvironmentLocationNotFound(prefix)
    print_export_header(context.subdir)
    print("@EXPLICIT")
    for prefix_record in PrefixData(prefix).iter_records_sorted():
        url = prefix_record.get("url")
        if not url or url.startswith(UNKNOWN_CHANNEL):
            print("# no URL for: %s" % prefix_record["fn"])
            continue
        md5 = prefix_record.get("md5")
        print(url + ("#%s" % md5 if add_md5 and md5 else ""))


def execute(args, parser):
    prefix = context.target_prefix
    if not is_conda_environment(prefix):
        from ..exceptions import EnvironmentLocationNotFound

        raise EnvironmentLocationNotFound(prefix)

    regex = args.regex
    if args.full_name:
        regex = r"^%s$" % regex

    if args.revisions:
        h = History(prefix)
        if isfile(h.path):
            if not context.json:
                h.print_log()
            else:
                stdout_json(h.object_log())
        else:
            from ..exceptions import PathNotFoundError

            raise PathNotFoundError(h.path)
        return

    if args.explicit:
        print_explicit(prefix, args.md5)
        return

    if args.canonical:
        format = "canonical"
    elif args.export:
        format = "export"
    else:
        format = "human"

    if context.json:
        format = "canonical"

    return print_packages(
        prefix,
        regex,
        format,
        reverse=args.reverse,
        piplist=args.pip,
        json=context.json,
        show_channel_urls=context.show_channel_urls,
    )
