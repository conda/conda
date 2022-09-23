# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from argparse import ArgumentParser, Namespace


def execute(args: Namespace, parser: ArgumentParser) -> None:
    parser.print_help()


if __name__ == "__main__":
    from ...argparse import do_call
    from ._parser import configure_parser

    parser = configure_parser()
    args = parser.parse_args()
    do_call(args, parser)
