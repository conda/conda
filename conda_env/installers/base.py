# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""DEPRECATED: Use `conda.env.installers.base` instead.

Dynamic installer loading.
"""
from conda.conda.exceptions import InvalidInstaller  # noqa
from conda.deprecations import deprecated
from conda.env.installers.base import get_installer  # noqa

deprecated.module("24.9", "25.3", addendum="Use `conda.env.installers.base` instead.")
