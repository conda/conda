# (c) Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from __future__ import print_function, division, absolute_import

import re
import os
import sys
import logging
from os.path import isdir, isfile, join
from argparse import RawDescriptionHelpFormatter

import conda.install as install
import conda.config as config
from conda.cli import common

from conda.egg_info import get_egg_info


descr = "List linked packages in a conda environment."

# Note, the formatting of this is designed to work well with help2man
examples = """
Examples:

List all packages in the current environment:

    conda list

List all packages installed into the environment 'myenv':

    conda list -n myenv

Save packages for future use:

    conda list --export > package-list.txt

Reinstall packages from an export file:

    conda create -n myenv --file package-list.txt

"""
log = logging.getLogger(__name__)

def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'list',
        description=descr,
        help=descr,
        formatter_class=RawDescriptionHelpFormatter,
        epilog=examples,
        add_help=False,
    )
    common.add_parser_help(p)
    common.add_parser_prefix(p)
    common.add_parser_json(p)
    common.add_parser_show_channel_urls(p)
    p.add_argument(
        '-c', "--canonical",
        action="store_true",
        help="Output canonical names of packages only. Implies --no-pip. ",
    )
    p.add_argument(
        '-f', "--full-name",
        action="store_true",
        help="Only search for full names, i.e., ^<regex>$.",
    )
    p.add_argument(
        "--explicit",
        action="store_true",
        help="List explicitly all installed conda packaged with URL "
             "(output may be used by conda create --file).",
    )
    p.add_argument(
        "--md5",
        action="store_true",
        help="Add MD5 hashsum when using --explicit",
    )
    p.add_argument(
        '-e', "--export",
        action="store_true",
        help="Output requirement string only (output may be used by "
             " conda create --file).",
    )
    p.add_argument(
        '-r', "--revisions",
        action="store_true",
        help="List the revision history and exit.",
    )
    p.add_argument(
        "--no-pip",
        action="store_false",
        default=True,
        dest="pip",
        help="Do not include pip-only installed packages.")
    p.add_argument(
        'regex',
        action="store",
        nargs="?",
        help="List only packages matching this regular expression.",
    )
    p.set_defaults(func=execute)


def print_export_header():
    print('# This file may be used to create an environment using:')
    print('# $ conda create --name <env> --file <this file>')
    print('# platform: %s' % config.subdir)


def get_packages(installed, regex):
    pat = re.compile(regex, re.I) if regex else None

    for dist in sorted(installed, key=str.lower):
        name = install.name_dist(dist)
        if pat and pat.search(name) is None:
            continue

        yield dist


def list_packages(prefix, installed, regex=None, format='human',
                  show_channel_urls=config.show_channel_urls):
    res = 1

    result = []
    for dist in get_packages(installed, regex):
        res = 0
        if format == 'canonical':
            result.append(dist)
            continue
        if format == 'export':
            result.append('='.join(dist.rsplit('-', 2)))
            continue

        try:
            # Returns None if no meta-file found (e.g. pip install)
            info = install.is_linked(prefix, dist)
            features = set(info.get('features', '').split())
            disp = '%(name)-25s %(version)-15s %(build)15s' % info
            disp += '  %s' % common.disp_features(features)
            schannel = info.get('schannel')
            if show_channel_urls or show_channel_urls is None and schannel != 'defaults':
                disp += '  %s' % schannel
            result.append(disp)
        except (AttributeError, IOError, KeyError, ValueError) as e:
            log.debug(str(e))
            result.append('%-25s %-15s %15s' % tuple(dist.rsplit('-', 2)))

    return res, result


def print_packages(prefix, regex=None, format='human', piplist=False,
                   json=False, show_channel_urls=config.show_channel_urls):
    if not isdir(prefix):
        common.error_and_exit("""\
Error: environment does not exist: %s
#
# Use 'conda create' to create an environment before listing its packages.""" %
                              prefix,
                              json=json,
                              error_type="NoEnvironmentFound")

    if not json:
        if format == 'human':
            print('# packages in environment at %s:' % prefix)
            print('#')
        if format == 'export':
            print_export_header()

    installed = install.linked(prefix)
    if piplist and config.use_pip and format == 'human':
        installed.update(get_egg_info(prefix))

    exitcode, output = list_packages(prefix, installed, regex, format=format,
                                     show_channel_urls=show_channel_urls)
    if not json:
        print('\n'.join(output))
    else:
        common.stdout_json(output)
    return exitcode


def print_explicit(prefix, add_md5=False):
    import json

    if not isdir(prefix):
        common.error_and_exit("Error: environment does not exist: %s" % prefix)
    print_export_header()
    print("@EXPLICIT")

    meta_dir = join(prefix, 'conda-meta')
    for fn in sorted(os.listdir(meta_dir)):
        if not fn.endswith('.json'):
            continue
        with open(join(meta_dir, fn)) as fi:
            meta = json.load(fi)
        url = meta.get('url')

        def format_url():
            return '%s%s-%s-%s.tar.bz2' % (meta['channel'], meta['name'],
                                           meta['version'], meta['build'])
        # two cases in which we want to try to format the url:
        # 1. There is no url key in the metadata
        # 2. The url key in the metadata is referencing a file on the local
        #    machine
        if not url:
            try:
                url = format_url()
            except KeyError:
                # Declare failure :-(
                print('# no URL for: %s' % fn[:-5])
                continue
        if url.startswith('file'):
            try:
                url = format_url()
            except KeyError:
                # declare failure and allow the url to be the file from which it was
                # originally installed
                continue
        md5 = meta.get('md5')
        print(url + ('#%s' % md5 if add_md5 and md5 else ''))


def execute(args, parser):
    prefix = common.get_prefix(args)

    regex = args.regex
    if args.full_name:
        regex = r'^%s$' % regex

    if args.revisions:
        from conda.history import History

        h = History(prefix)
        if isfile(h.path):
            if not args.json:
                h.print_log()
            else:
                common.stdout_json(h.object_log())
        else:
            common.error_and_exit("No revision log found: %s\n" % h.path,
                                  json=args.json,
                                  error_type="NoRevisionLog")
        return

    if args.explicit:
        print_explicit(prefix, args.md5)
        return

    if args.canonical:
        format = 'canonical'
    elif args.export:
        format = 'export'
    else:
        format = 'human'

    if args.json:
        format = 'canonical'

    exitcode = print_packages(prefix, regex, format, piplist=args.pip,
                              json=args.json,
                              show_channel_urls=args.show_channel_urls)
    sys.exit(exitcode)
