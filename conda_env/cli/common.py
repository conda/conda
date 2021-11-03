# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import os
from os.path import isdir, join
import sys

from conda.auxlib.entity import EntityEncoder
from conda.auxlib.path import expand
from conda.base.context import context
from conda.cli import install as cli_install
from conda.cli import common as cli_common
from conda.gateways.connection.session import CONDA_SESSION_SCHEMES

base_env_name = 'base'


def stdout_json(d):
    import json

    json.dump(d, sys.stdout, indent=2, sort_keys=True, cls=EntityEncoder)
    sys.stdout.write('\n')


def get_prefix(args, search=True):
    from conda.base.context import determine_target_prefix
    return determine_target_prefix(context, args)


def find_prefix_name(name):
    if name == base_env_name:
        return context.root_prefix
    # always search cwd in addition to envs dirs (for relative path access)
    for envs_dir in list(context.envs_dirs) + [os.getcwd(), ]:
        prefix = join(envs_dir, name)
        if isdir(prefix):
            return prefix
    return None


def print_result(args, prefix, result):
    if context.json:
        if result["conda"] is None and result["pip"] is None:
            cli_common.stdout_json_success(message='All requested packages already installed.')
        else:
            if result["conda"] is not None:
                actions = result["conda"]
            else:
                actions = {}
            if result["pip"] is not None:
                actions["PIP"] = result["pip"]
            cli_common.stdout_json_success(prefix=prefix, actions=actions)
    else:
        cli_install.print_activate(args.name if args.name else prefix)


def get_filename(filename):
    """Expand filename if local path or return the url"""
    url_scheme = filename.split("://", 1)[0]
    if url_scheme in CONDA_SESSION_SCHEMES:
        return filename
    else:
        return expand(filename)
