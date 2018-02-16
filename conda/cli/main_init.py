# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from logging import getLogger

from ..base.context import context
from ..common.compat import on_win

log = getLogger(__name__)


def execute(args, parser):
    from ..initialize import ALL_SHELLS, initialize, initialize_dev, install

    selected_shells = tuple(s for s in ALL_SHELLS if getattr(args, s, None))
    if not selected_shells:
        selected_shells = ('cmd_exe' if on_win else 'bash',)

    if args.dev:
        assert len(selected_shells) == 1, selected_shells
        return initialize_dev(selected_shells[0])

    elif args.install_only:
        return install(context.conda_prefix)

    else:
        if not (args.install_only and args.user and args.system):
            args.user = True
        return initialize(context.conda_prefix, selected_shells, args.user, args.system)
