# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from logging import getLogger

from ..base.context import context
from ..common.compat import on_win
from ..exceptions import ArgumentError

log = getLogger(__name__)


def execute(args, parser):
    from ..base.constants import COMPATIBLE_SHELLS
    from ..core.initialize import initialize, initialize_dev, install

    if args.install:
        return install(context.conda_prefix)

    if args.all:
        selected_shells = COMPATIBLE_SHELLS
    else:
        selected_shells = tuple(args.shells)

    if args.dev:
        if len(selected_shells) != 1:
            raise ArgumentError("--dev can only handle one shell at a time right now")
        return initialize_dev(selected_shells[0])

    else:
        for_user = args.user and not args.system
        anaconda_prompt = on_win and args.anaconda_prompt
        return initialize(
            context.conda_prefix,
            selected_shells,
            for_user,
            args.system,
            anaconda_prompt,
            args.reverse,
        )
