# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations
from typing import TYPE_CHECKING

from ....core.envs_manager import list_all_known_prefixes
from ...common import print_envs_list, stdout_json

if TYPE_CHECKING:
    from argparse import ArgumentParser, Namespace


def execute(args: Namespace, parser: ArgumentParser) -> None:
    info_dict = {"envs": list_all_known_prefixes()}
    print_envs_list(info_dict["envs"], not args.json)

    if args.json:
        stdout_json(info_dict)


if __name__ == "__main__":
    from ._parser import configure_parser

    parser = configure_parser()
    args = parser.parse_args()
    execute(args, parser)
