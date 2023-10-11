# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""DEPRECATED: Use `conda.env.installers.base` instead.

Dynamic installer loading.
"""
from conda.deprecations import deprecated
from conda.env.installers.base import InvalidInstaller, get_installer  # noqa

deprecated.module("24.3", "24.9", addendum="Use `conda.env.installers.base` instead.")
