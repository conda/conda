# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""DEPRECATED: Use `conda.env.installers.pip` instead.

Pip-flavored installer.
"""
from conda.deprecations import deprecated

deprecated.module("24.9", "25.3", addendum="Use `conda.env.installers.pip` instead.")
