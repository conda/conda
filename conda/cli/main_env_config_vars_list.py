# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from argparse import ArgumentParser, Namespace
from os.path import lexists

from ..base.context import context, determine_target_prefix
from .common import stdout_json
from ..core.prefix_data import PrefixData
from ..exceptions import EnvironmentLocationNotFound


def execute(args: Namespace, parser: ArgumentParser):
    prefix = determine_target_prefix(context, args)
    if not lexists(prefix):
        raise EnvironmentLocationNotFound(prefix)

    pd = PrefixData(prefix)

    env_vars = pd.get_environment_env_vars()
    if args.json:
        stdout_json(env_vars)
    else:
        for k, v in env_vars.items():
            print(f"{k} = {v}")
