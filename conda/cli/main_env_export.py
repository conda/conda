# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from argparse import ArgumentParser, Namespace

from ..base.context import context, determine_target_prefix, env_name
from .common import stdout_json
from conda_env.env import from_environment


# TODO Make this aware of channels that were used to install packages
def execute(args: Namespace, parser: ArgumentParser):
    prefix = determine_target_prefix(context, args)
    env = from_environment(
        env_name(prefix),
        prefix,
        no_builds=args.no_builds,
        ignore_channels=args.ignore_channels,
        from_history=args.from_history,
    )

    if args.override_channels:
        env.remove_channels()

    if args.channel is not None:
        env.add_channels(args.channel)

    if args.file is None:
        stdout_json(env.to_dict()) if args.json else print(env.to_yaml(), end="")
    else:
        fp = open(args.file, "wb")
        env.to_dict(stream=fp) if args.json else env.to_yaml(stream=fp)
        fp.close()
