# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Register the classic conda solver."""

from ..deprecations import deprecated

deprecated.module(
    "25.9.0",
    "26.3.0",
    addendum="Use `conda_classic_solver.plugin`.",
)


def conda_solvers():
    # Deprecated. Use `conda_classic_solver.plugin`
    pass
