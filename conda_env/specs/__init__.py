# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""DEPRECATED: Use `conda.env.specs` instead.

Dynamic installer loading.
"""
from conda.deprecations import deprecated
from conda.env.specs import detect, get_spec_class_from_file  # noqa

deprecated.module("24.3", "24.9", addendum="Use `conda.env.specs` instead.")
