# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

"""Common utilities for the conda env sub-command."""
from os.path import abspath, expanduser, expandvars

from ..base.context import context
from ..cli import install
from ..cli.common import stdout_json_success
from ..gateways.connection.session import CONDA_SESSION_SCHEMES


def get_filename(filename):
    """Expand filename if local path or return the ``url``"""
    url_scheme = filename.split("://", 1)[0]
    if url_scheme in CONDA_SESSION_SCHEMES:
        return filename
    else:
        return abspath(expanduser(expandvars(filename)))


def print_result(args, prefix, result):
    """Print the result of an install operation"""
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
        install.print_activate(args.name or prefix)
