# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""DEPRECATED: Use `conda.env.installers.base` instead.

Dynamic installer loading.
"""
# Import conda.cli.main_env_vars since this module is deprecated.
from conda.deprecations import deprecated
from conda.env.installers.base import InvalidInstaller, get_installer  # noqa

deprecated.module("23.9", "24.3", addendum="Use `conda.env.installers.base` instead.")
