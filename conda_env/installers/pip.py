# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""DEPRECATED: Use `conda.env.installers.pip` instead.

Pip-flavored installer.
"""
from conda.deprecations import deprecated
from conda.env.installers.pip import install  # noqa

deprecated.module("23.9", "24.3", addendum="Use `conda.env.installers.pip` instead.")
