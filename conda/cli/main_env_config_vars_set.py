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

    env_vars_to_add = {}
    for v in args.vars:
        var_def = v.split("=")
        env_vars_to_add[var_def[0].strip()] = "=".join(var_def[1:]).strip()
    pd.set_environment_env_vars(env_vars_to_add)
    if prefix == context.active_prefix:
        print("To make your changes take effect please reactivate your environment")
