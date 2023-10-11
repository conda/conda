# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""DEPRECATED: Use `conda.cli.main_env_vars` instead.

CLI implementation for `conda-env config vars`.

Allows for configuring conda-env's vars.
"""
# Import conda.cli.main_env_vars since this module is deprecated.
from conda.cli.main_env_vars import (  # noqa
    configure_parser,
    execute_list,
    execute_set,
    execute_unset,
)
from conda.deprecations import deprecated

deprecated.module("24.3", "24.9", addendum="Use `conda.cli.main_env_vars` instead.")
