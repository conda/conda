# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""DEPRECATED: Use `conda.cli.main_env` instead.

Entry point for all conda-env subcommands.
"""
from conda.cli.main_env import configure_parser, execute  # noqa
from conda.deprecations import deprecated

deprecated.module("23.9", "24.3", addendum="Use `conda.cli.main_env` instead.")
