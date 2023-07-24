# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Detect cuda version."""
from ..deprecations import deprecated
from ..plugins.virtual_packages import cuda

deprecated.module(
    "23.3", "23.9", addendum="Use `conda.plugins.virtual_packages.cuda` instead."
)


@deprecated(
    "23.3",
    "23.9",
    addendum="Use `conda.plugins.virtual_packages.cuda.cuda_version` instead.",
)
def cuda_detect():
    return cuda.cuda_version()
