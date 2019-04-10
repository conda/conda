# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import absolute_import, division, print_function, unicode_literals

from logging import getLogger

from ..base.context import context
from ..common.compat import on_win

log = getLogger(__name__)


def execute(args, parser):
    from ..base.constants import COMPATIBLE_SHELLS
    from ..core.initialize import initialize, initialize_dev, install

    if args.install:
        return install(context.conda_prefix)

    invalid_shells = tuple(s for s in args.shells if s not in COMPATIBLE_SHELLS)
    if invalid_shells:
        from ..exceptions import ArgumentError
        from ..common.io import dashlist
        raise ArgumentError("Invalid shells: %s\n\n"
                            "Currently available shells are:%s"
                            % (dashlist(invalid_shells), dashlist(sorted(COMPATIBLE_SHELLS))))

    if args.all:
        selected_shells = COMPATIBLE_SHELLS
    else:
        selected_shells = tuple(args.shells)

    if not selected_shells:
        selected_shells = ('cmd.exe', 'powershell') if on_win else ('bash',)

    if args.dev:
        assert len(selected_shells) == 1, "--dev can only handle one shell at a time right now"
        shell = selected_shells[0]
        return initialize_dev(shell)

    else:
        for_user = args.user
        if not (args.install and args.user and args.system):
            for_user = True
        if args.no_user:
            for_user = False

        anaconda_prompt = on_win and args.anaconda_prompt
        return initialize(context.conda_prefix, selected_shells, for_user, args.system,
                          anaconda_prompt, args.reverse)
