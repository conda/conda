# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from argparse import ArgumentParser, Namespace

from .common import print_envs_list, stdout_json
from ..core.envs_manager import list_all_known_prefixes


def execute(args: Namespace, parser: ArgumentParser):
    info_dict = {"envs": list_all_known_prefixes()}
    print_envs_list(info_dict["envs"], not args.json)

    if args.json:
        stdout_json(info_dict)
