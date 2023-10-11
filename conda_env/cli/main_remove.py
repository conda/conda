# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""DEPRECATED: Use `conda.cli.main_env_remove` instead.

CLI implementation for `conda-env remove`.

Removes the specified conda environment.
"""
# Import from conda.cli.main_env_remove since this module is deprecated.
from conda.cli.main_env_remove import configure_parser, execute  # noqa
from conda.deprecations import deprecated

deprecated.module("24.3", "24.9", addendum="Use `conda.cli.main_env_remove` instead.")
