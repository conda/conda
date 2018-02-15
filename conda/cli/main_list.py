# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from __future__ import absolute_import, division, print_function, unicode_literals

import logging
from os.path import isdir, isfile
import re

from .common import disp_features, stdout_json
from ..base.constants import DEFAULTS_CHANNEL_NAME, UNKNOWN_CHANNEL
from ..base.context import context
from ..common.compat import text_type
from ..core.prefix_data import PrefixData, is_linked, linked
from ..egg_info import get_egg_info
from ..gateways.disk.test import is_conda_environment
from ..history import History

log = logging.getLogger(__name__)


def print_export_header(subdir):
    print('# This file may be used to create an environment using:')
    print('# $ conda create --name <env> --file <this file>')
    print('# platform: %s' % subdir)


def get_packages(installed, regex):
    pat = re.compile(regex, re.I) if regex else None
    for dist in sorted(installed, key=lambda x: x.quad[0].lower()):
        name = dist.quad[0]
        if pat and pat.search(name) is None:
            continue

        yield dist


def list_packages(prefix, installed, regex=None, format='human',
                  show_channel_urls=None):
    res = 0
    result = []

    if format == 'human':
        result.append('# packages in environment at %s:' % prefix)
        result.append('#')
        result.append('# %-23s %-15s %15s  Channel' % ("Name", "Version", "Build"))

    for dist in get_packages(installed, regex):
        if format == 'canonical':
            result.append(dist)
            continue
        if format == 'export':
            result.append('='.join(dist.quad[:3]))
            continue

        try:
            # Returns None if no meta-file found (e.g. pip install)
            info = is_linked(prefix, dist)
            if info is None:
                result.append('%-25s %-15s %15s' % tuple(dist.quad[:3]))
            else:
                features = set(info.get('features') or ())
                disp = '%(name)-25s %(version)-15s %(build)15s' % info  # NOQA lgtm [py/percent-format/wrong-arguments]
                disp += '  %s' % disp_features(features)
                schannel = info.get('schannel')
                show_channel_urls = show_channel_urls or context.show_channel_urls
                if (show_channel_urls or show_channel_urls is None
                        and schannel != DEFAULTS_CHANNEL_NAME):
                    disp += '  %s' % schannel
                result.append(disp)
        except (AttributeError, IOError, KeyError, ValueError) as e:
            log.debug("exception for dist %s:\n%r", dist, e)
            result.append('%-25s %-15s %15s' % tuple(dist.quad[:3]))

    return res, result


def print_packages(prefix, regex=None, format='human', piplist=False,
                   json=False, show_channel_urls=None):
    if not isdir(prefix):
        from ..exceptions import EnvironmentLocationNotFound
        raise EnvironmentLocationNotFound(prefix)

    if not json:
        if format == 'export':
            print_export_header(context.subdir)

    installed = linked(prefix)
    log.debug("installed conda packages:\n%s", installed)
    if piplist and context.use_pip and format == 'human':
        other_python = get_egg_info(prefix)
        log.debug("other installed python packages:\n%s", other_python)
        installed.update(other_python)

    exitcode, output = list_packages(prefix, installed, regex, format=format,
                                     show_channel_urls=show_channel_urls)
    if context.json:
        stdout_json(output)

    else:
        print('\n'.join(map(text_type, output)))

    return exitcode


def print_explicit(prefix, add_md5=False):
    if not isdir(prefix):
        from ..exceptions import EnvironmentLocationNotFound
        raise EnvironmentLocationNotFound(prefix)
    print_export_header(context.subdir)
    print("@EXPLICIT")
    for prefix_record in PrefixData(prefix).iter_records_sorted():
        url = prefix_record.get('url')
        if not url or url.startswith(UNKNOWN_CHANNEL):
            print('# no URL for: %s' % prefix_record['fn'])
            continue
        md5 = prefix_record.get('md5')
        print(url + ('#%s' % md5 if add_md5 and md5 else ''))


def execute(args, parser):
    prefix = context.target_prefix
    if not is_conda_environment(prefix):
        from ..exceptions import EnvironmentLocationNotFound
        raise EnvironmentLocationNotFound(prefix)

    regex = args.regex
    if args.full_name:
        regex = r'^%s$' % regex

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
        format = 'canonical'
    elif args.export:
        format = 'export'
    else:
        format = 'human'
    if context.json:
        format = 'canonical'

    exitcode = print_packages(prefix, regex, format, piplist=args.pip,
                              json=context.json,
                              show_channel_urls=context.show_channel_urls)
    return exitcode
