# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations
from os.path import lexists
from typing import TYPE_CHECKING

from ......base.context import context, determine_target_prefix
from ......core.prefix_data import PrefixData
from ......exceptions import EnvironmentLocationNotFound

if TYPE_CHECKING:
    from argparse import ArgumentParser, Namespace


def execute(args: Namespace, parser: ArgumentParser) -> None:
    prefix = determine_target_prefix(context, args)
    pd = PrefixData(prefix)
    if not lexists(prefix):
        raise EnvironmentLocationNotFound(prefix)

    env_vars_to_add = {}
    for v in args.vars:
        var_def = v.split("=")
        env_vars_to_add[var_def[0].strip()] = "=".join(var_def[1:]).strip()
    pd.set_environment_env_vars(env_vars_to_add)
    if prefix == context.active_prefix:
        print("To make your changes take effect please reactivate your environment")


if __name__ == "__main__":
    from ._parser import configure_parser

    parser = configure_parser()
    args = parser.parse_args()
    execute(args, parser)
