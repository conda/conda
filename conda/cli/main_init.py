# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from logging import getLogger

from ..base.context import context
from ..common.compat import on_win

log = getLogger(__name__)


def execute(args, parser):
    from ..initialize import ALL_SHELLS, initialize, initialize_dev, install

    if args.install:
        return install(context.conda_prefix)

    invalid_shells = tuple(s for s in args.shells if s not in ALL_SHELLS)
    if invalid_shells:
        from ..exceptions import ArgumentError
        from ..resolve import dashlist  # TODO: this import is ridiculous; move it to common!
        raise ArgumentError("Invalid shells: %s" % dashlist(invalid_shells))

    selected_shells = tuple(args.shells)
    if not selected_shells:
        selected_shells = ('cmd_exe' if on_win else 'bash',)

    if args.dev:
        assert len(selected_shells) == 1, selected_shells
        shell = selected_shells[0]
        # assert shell == 'bash'
        return initialize_dev(shell)

    else:
        for_user = args.user
        if not (args.install and args.user and args.system):
            for_user = True
        if args.no_user:
            for_user = False

        desktop_prompt = on_win and args.desktop_prompt
        return initialize(context.conda_prefix, selected_shells, for_user, args.system,
                          desktop_prompt)
