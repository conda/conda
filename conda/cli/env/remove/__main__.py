# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from argparse import ArgumentParser, Namespace


def execute(args: Namespace, parser: ArgumentParser) -> None:
    import conda.cli.main_remove

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
    from conda.base.context import context

    context.__init__(argparse_args=args)

    conda.cli.main_remove.execute(args, parser)


if __name__ == "__main__":
    from ._parser import configure_parser

    parser = configure_parser()
    args = parser.parse_args()
    execute(args, parser)
