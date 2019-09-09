# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from argparse import RawDescriptionHelpFormatter

from conda.cli import common
from conda.cli.conda_argparse import add_parser_prefix, add_parser_json
from conda.core.prefix_data import PrefixData
from conda.base.context import context
from .common import get_prefix


description = """
Interact with environment varaibles associated with Conda environments
"""

example = """
examples:
    conda env vars --list -n my_env
    conda env vars --set MY_VAR=something
    conda env vars --unset MY_VAR
"""


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'vars',
        formatter_class=RawDescriptionHelpFormatter,
        description=description,
        help=description,
        epilog=example,
    )

    p.add_argument(
        '-l', '--list',
        action="store_true",
        default=None,
        help='list environment variables',
    )

    p.add_argument(
        '-s', '--set',
        action='store',
        help='set environment variables',
        default=None,
    )

    p.add_argument(
        '-u', '--unset',
        action='store',
        help='unset environment variables',
        default=None,
    )

    # Add name and prefix args
    add_parser_prefix(p)
    add_parser_json(p)
    p.set_defaults(func='.main_vars.execute')


def execute(args, parser):
    prefix = get_prefix(args, search=False) or context.active_prefix
    pd = PrefixData(prefix)

    if args.list:
        env_vars = pd.get_environment_env_vars()
        if args.json:
            common.stdout_json(env_vars)
        else:
            for k, v in env_vars.items():
                print("%s = %s" % (k, v))

    if args.set:
        vars = args.set.split(',')
        env_vars_to_add = {}
        for v in vars:
            var_def = v.split("=")
            env_vars_to_add[var_def[0].strip()] = var_def[-1].strip()
        pd.set_environment_env_vars(env_vars_to_add)

    if args.unset:
        vars_to_unset = [_.strip() for _ in args.unset.split(',')]
        pd.unset_environment_env_vars(vars_to_unset)
