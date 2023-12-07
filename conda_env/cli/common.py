# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""DEPRECATED: Use `conda.cli.common` instead.

Common utilities for conda-env command line tools.
"""
# Import conda.cli.main_env_vars since this module is deprecated.
from conda.base.constants import ROOT_ENV_NAME
from conda.cli.common import get_filename, print_result  # noqa: F401
from conda.deprecations import deprecated

deprecated.module("24.3", "24.9", addendum="Use `conda.cli.common` instead.")
deprecated.constant(
    "24.3",
    "24.9",
    "base_env_name",
    ROOT_ENV_NAME,
    addendum="Use `conda.base.constants.ROOT_ENV_NAME` instead.",
)
