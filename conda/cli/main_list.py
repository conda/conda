# (c) Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from __future__ import print_function, division, absolute_import

import re
import sys
import subprocess
from os.path import isdir, isfile
import logging

import conda.install as install
import conda.config as config
from conda.cli import common

# pip_args is here for BC
from conda.pip import pip_args, add_pip_installed


descr = "List linked packages in a conda environment."

log = logging.getLogger(__name__)

def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'list',
        description = descr,
        help = descr,
    )
    common.add_parser_prefix(p)
    common.add_parser_json(p)
    p.add_argument(
        '-c', "--canonical",
        action = "store_true",
        help = "output canonical names of packages only",
    )
    p.add_argument(
        '-e', "--export",
        action = "store_true",
        help = "output requirement string only "
                  "(output may be used by conda create --file)",
    )
    p.add_argument(
        '-r', "--revisions",
        action = "store_true",
        help = "list the revision history and exit",
    )
    p.add_argument(
        "--no-pip",
        action = "store_false",
        default=True,
        dest="pip",
        help = "Do not include pip-only installed packages")
    p.add_argument(
        'regex',
        action = "store",
        nargs = "?",
        help = "list only packages matching this regular expression",
    )
    p.set_defaults(func=execute)


def print_export_header():
    print('# This file may be used to create an environment using:')
    print('# $ conda create --name <env> --file <this file>')
    print('# platform: %s' % config.subdir)


def get_packages(installed, regex):
    pat = re.compile(regex, re.I) if regex else None

    for dist in sorted(installed):
        name = dist.rsplit('-', 2)[0]
        if pat and pat.search(name) is None:
            continue

        yield dist


def list_packages(prefix, installed, regex=None, format='human'):
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
            if config.show_channel_urls:
                disp += '  %s' % config.canonical_channel_name(info.get('url'))
            result.append(disp)
        except (AttributeError, IOError, KeyError, ValueError) as e:
            log.debug(str(e))
            result.append('%-25s %-15s %15s' % tuple(dist.rsplit('-', 2)))

    return res, result


def print_packages(prefix, regex=None, format='human', piplist=False, json=False):
    if not isdir(prefix):
        common.error_and_exit("""\
Error: environment does not exist: %s
#
# Use 'conda create' to create an environment before listing its packages.""" % prefix,
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
        add_pip_installed(prefix, installed, json=json)

    exitcode, output = list_packages(prefix, installed, regex, format=format)
    if not json:
        print('\n'.join(output))
    else:
        common.stdout_json(output)
    sys.exit(exitcode)


def execute(args, parser):
    prefix = common.get_prefix(args)

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

    if args.canonical:
        format = 'canonical'
    elif args.export:
        format = 'export'
    else:
        format = 'human'

    if args.json:
        format = 'canonical'

    print_packages(prefix, args.regex, format, piplist=args.pip, json=args.json)
