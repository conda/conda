# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations
from os.path import lexists
from typing import TYPE_CHECKING

from conda.base.context import context, determine_target_prefix
from conda.cli import common
from conda.core.prefix_data import PrefixData
from conda.exceptions import EnvironmentLocationNotFound

if TYPE_CHECKING:
    from argparse import ArgumentParser, Namespace


def execute(args: Namespace, parser: ArgumentParser) -> None:
    prefix = determine_target_prefix(context, args)
    if not lexists(prefix):
        raise EnvironmentLocationNotFound(prefix)

    pd = PrefixData(prefix)

    env_vars = pd.get_environment_env_vars()
    if args.json:
        common.stdout_json(env_vars)
    else:
        for k, v in env_vars.items():
            print("%s = %s" % (k, v))


if __name__ == "__main__":
    from ._parser import configure_parser

    parser = configure_parser()
    args = parser.parse_args()
    execute(args, parser)
