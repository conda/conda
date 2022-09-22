# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations
from typing import TYPE_CHECKING

from ....base.context import context, determine_target_prefix, env_name
from ....cli.common import stdout_json
from ..env import from_environment

if TYPE_CHECKING:
    from argparse import ArgumentParser, Namespace


# TODO Make this aware of channels that were used to install packages
def execute(args: Namespace, parser: ArgumentParser) -> None:
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


if __name__ == "__main__":
    from ._parser import configure_parser

    parser = configure_parser()
    args = parser.parse_args()
    execute(args, parser)
