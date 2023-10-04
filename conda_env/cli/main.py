# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""DEPRECATED: Use `conda.env.cli.main` instead.

Entry point for all conda-env subcommands.
"""
from conda.deprecations import deprecated

deprecated.module("23.9", "24.3", addendum="Use `conda.env.cli.main` instead.")
