# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import os
from os.path import isdir, join, abspath, expanduser, expandvars
import warnings

from conda.base.context import context, determine_target_prefix
from conda.cli import install as cli_install
from conda.cli.common import stdout_json as _stdout_json, stdout_json_success
from conda.gateways.connection.session import CONDA_SESSION_SCHEMES

base_env_name = 'base'


def stdout_json(d):
    warnings.warn(
        "`conda_env.cli.common.stdout_json` is pending deprecation and will be removed in a "
        "future release. Please use `conda.cli.common.stdout_json` instead.",
        PendingDeprecationWarning,
    )
    _stdout_json(d)


def get_prefix(args, search=True):
    warnings.warn(
        "`conda_env.cli.common.get_prefix` is pending deprecation and will be removed in a future "
        "release. Please use `conda.base.context.determine_target_prefix` instead.",
        PendingDeprecationWarning,
    )
    return determine_target_prefix(context, args)


def find_prefix_name(name):
    warnings.warn(
        "`conda_env.cli.common.find_prefix_name` is pending deprecation and will be removed in a "
        "future release.",
        PendingDeprecationWarning,
    )
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
            stdout_json_success(message="All requested packages already installed.")
        else:
            if result["conda"] is not None:
                actions = result["conda"]
            else:
                actions = {}
            if result["pip"] is not None:
                actions["PIP"] = result["pip"]
            stdout_json_success(prefix=prefix, actions=actions)
    else:
        cli_install.print_activate(args.name if args.name else prefix)


def get_filename(filename):
    """Expand filename if local path or return the url"""
    url_scheme = filename.split("://", 1)[0]
    if url_scheme in CONDA_SESSION_SCHEMES:
        return filename
    else:
        return abspath(expanduser(expandvars(filename)))
