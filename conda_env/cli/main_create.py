# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""DEPRECATED: Use `conda.cli.main_env_create` instead.

CLI implementation for `conda-env create`.

Creates new conda environments with the specified packages.
"""
# Import from conda.cli.main_env_create since this module is deprecated.
from conda.cli.main_env_create import configure_parser, execute  # noqa
from conda.deprecations import deprecated

deprecated.module("24.3", "24.9", addendum="Use `conda.cli.main_env_create` instead.")
