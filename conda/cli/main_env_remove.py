# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from argparse import ArgumentParser, Namespace

from . import main_remove
from ..base.context import context


def execute(args: Namespace, parser: ArgumentParser):
    args = vars(args)
    args.update(
        {
            "all": True,
            "channel": None,
            "features": None,
            "override_channels": None,
            "use_local": None,
            "use_cache": None,
            "offline": None,
            "force": True,
            "pinned": None,
        }
    )
    args = Namespace(**args)
    context.__init__(argparse_args=args)

    main_remove.execute(args, parser)
