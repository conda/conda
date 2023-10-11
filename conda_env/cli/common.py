# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""DEPRECATED: Use `conda.env.cli.common` instead.

Common utilities for conda-env command line tools.
"""
# Import conda.cli.main_env_vars since this module is deprecated.
from conda.deprecations import deprecated
from conda.env.cli.common import get_filename, print_result  # noqa

deprecated.module("24.3", "24.9", addendum="Use `conda.env.cli.common` instead.")
