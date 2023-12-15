# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""DEPRECATED: Use `conda.cli.main_env_config` instead.

CLI implementation for `conda-env config`.

Allows for programmatically interacting with conda-env's configuration files (e.g., `~/.condarc`).
"""
# Import from conda.cli.main_env_config since this module is deprecated.
from conda.cli.main_env_config import configure_parser, execute  # noqa
from conda.deprecations import deprecated

deprecated.module("24.9", "25.3", addendum="Use `conda.cli.main_env_config` instead.")
