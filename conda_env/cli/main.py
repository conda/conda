# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""DEPRECATED: Use `conda.env.cli.main` instead.

Entry point for all conda-env subcommands.
"""
# Import from conda.env.cli.main since this module is deprecated.
from conda.env.cli.main import (  # noqa
    create_parser,
    do_call,
    show_help_on_empty_command,
)
from conda.deprecations import deprecated

deprecated.module("23.9", "24.3", addendum="Use `conda.env.cli.main` instead.")
