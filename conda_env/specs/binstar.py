# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""DEPRECATED: Use `conda.env.specs.binstar` instead.

Define binstar spec.
"""
from conda.deprecations import deprecated
from conda.env.specs.binstar import BinstarSpec  # noqa

deprecated.module("24.9", "25.3", addendum="Use `conda.env.specs.binstar` instead.")
