# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import os
from os.path import abspath, expanduser, expandvars, isdir, join

from conda.base.context import context, determine_target_prefix
from conda.cli import install as cli_install
from conda.cli.common import stdout_json as _stdout_json
from conda.cli.common import stdout_json_success
from conda.deprecations import deprecated
from conda.gateways.connection.session import CONDA_SESSION_SCHEMES

base_env_name = "base"


@deprecated("23.3", "23.9", addendum="Use `conda.cli.common.stdout_json` instead.")
def stdout_json(d):
    _stdout_json(d)


@deprecated(
    "23.3", "23.9", addendum="Use `conda.base.context.determine_target_prefix` instead."
)
def get_prefix(args, search=True):
    return determine_target_prefix(context, args)


@deprecated("23.3", "23.9")
def find_prefix_name(name):
    if name == base_env_name:
        return context.root_prefix
    # always search cwd in addition to envs dirs (for relative path access)
    for envs_dir in list(context.envs_dirs) + [
        os.getcwd(),
    ]:
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
        cli_install.print_activate(args.name or prefix)


def get_filename(filename):
    """Expand filename if local path or return the url"""
    url_scheme = filename.split("://", 1)[0]
    if url_scheme in CONDA_SESSION_SCHEMES:
        return filename
    else:
        return abspath(expanduser(expandvars(filename)))
