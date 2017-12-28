# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from logging import getLogger

from ..base.context import context
from ..common.compat import on_win

log = getLogger(__name__)


def execute(args, parser):
    from ..initialize import ALL_SHELLS, initialize, initialize_dev

    if args.dev:
        return initialize_dev()

    selected_shells = set(s for s in ALL_SHELLS if getattr(args, s, None))
    if not selected_shells:
        selected_shells.add('cmd_exe' if on_win else 'bash')

    if not (args.user and args.system):
        args.user = True

    initialize(context.conda_prefix, args.auto_activate, selected_shells, args.user, args.system)
