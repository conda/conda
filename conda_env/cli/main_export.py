# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import absolute_import, print_function

from argparse import RawDescriptionHelpFormatter
import os
import textwrap

from conda.cli.conda_argparse import add_parser_json, add_parser_prefix

# conda env import
from .common import get_prefix, stdout_json
from ..env import from_environment
from ..exceptions import CondaEnvException

description = """
Export a given environment
"""

example = """
examples:
    conda env export
    conda env export --file SOME_FILE
"""


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'export',
        formatter_class=RawDescriptionHelpFormatter,
        description=description,
        help=description,
        epilog=example,
    )

    p.add_argument(
        '-c', '--channel',
        action='append',
        help='Additional channel to include in the export'
    )

    p.add_argument(
        "--override-channels",
        action="store_true",
        help="Do not include .condarc channels",
    )
    add_parser_prefix(p)

    p.add_argument(
        '-f', '--file',
        default=None,
        required=False
    )

    p.add_argument(
        '--no-builds',
        default=False,
        action='store_true',
        required=False,
        help='Remove build specification from dependencies'
    )

    p.add_argument(
        '--ignore-channels',
        default=False,
        action='store_true',
        required=False,
        help='Do not include channel names with package names.')
    add_parser_json(p)

    p.add_argument(
        '--from-history',
        default=False,
        action='store_true',
        required=False,
        help='Build environment spec from explicit specs in history'
    )
    p.set_defaults(func='.main_export.execute')


# TODO Make this aware of channels that were used to install packages
def execute(args, parser):
    if not (args.name or args.prefix):
        # Note, this is a hack fofr get_prefix that assumes argparse results
        # TODO Refactor common.get_prefix
        name = os.environ.get('CONDA_DEFAULT_ENV', False)
        prefix = os.environ.get('CONDA_PREFIX', False)
        if not (name or prefix):
            msg = "Unable to determine environment\n\n"
            msg += textwrap.dedent("""
                Please re-run this command with one of the following options:

                * Provide an environment name via --name or -n
                * Re-run this command inside an activated conda environment.""").lstrip()
            # TODO Add json support
            raise CondaEnvException(msg)
        if name:
            if os.sep in name:
                # assume "names" with a path seperator are actually paths
                args.prefix = name
            else:
                args.name = name
        else:
            args.prefix = prefix
    else:
        name = args.name
    prefix = get_prefix(args)
    env = from_environment(name, prefix, no_builds=args.no_builds,
                           ignore_channels=args.ignore_channels, from_history=args.from_history)

    if args.override_channels:
        env.remove_channels()

    if args.channel is not None:
        env.add_channels(args.channel)

    if args.file is None:
        stdout_json(env.to_dict()) if args.json else print(env.to_yaml(), end='')
    else:
        fp = open(args.file, 'wb')
        env.to_dict(stream=fp) if args.json else env.to_yaml(stream=fp)
        fp.close()
