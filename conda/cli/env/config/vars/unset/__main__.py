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

    vars_to_unset = [_.strip() for _ in args.vars]
    pd.unset_environment_env_vars(vars_to_unset)
    if prefix == context.active_prefix:
        print("To make your changes take effect please reactivate your environment")


if __name__ == "__main__":
    from .....argparse import do_call
    from ._parser import configure_parser

    parser = configure_parser()
    args = parser.parse_args()
    do_call(args, parser)
