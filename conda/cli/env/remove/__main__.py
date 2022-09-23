# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations
from typing import TYPE_CHECKING

from ....base.context import context
from ...main_remove import execute_remove

if TYPE_CHECKING:
    from argparse import ArgumentParser, Namespace


def execute(args: Namespace, parser: ArgumentParser) -> None:
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
    execute_remove(args, parser)


if __name__ == "__main__":
    from ...argparse import do_call
    from ._parser import configure_parser

    parser = configure_parser()
    args = parser.parse_args()
    do_call(args, parser)
