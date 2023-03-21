# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from argparse import ArgumentParser, Namespace
from os.path import lexists

from ..base.context import context, determine_target_prefix
from ..core.prefix_data import PrefixData
from ..exceptions import EnvironmentLocationNotFound


def execute(args: Namespace, parser: ArgumentParser) -> bool:
    prefix = determine_target_prefix(context, args)
    pd = PrefixData(prefix)
    if not lexists(prefix):
        raise EnvironmentLocationNotFound(prefix)

    vars_to_unset = [_.strip() for _ in args.vars]
    pd.unset_environment_env_vars(vars_to_unset)
    if prefix == context.active_prefix:
        print("To make your changes take effect please reactivate your environment")
