# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Register the classic conda solver."""

from ..deprecations import deprecated

deprecated.module(
    "25.1.0",
    "25.7.0",
    "Use `conda_classic_solver.plugin`.",
)


def conda_solvers():
    # Deprecated. Use `conda_classic_solver.plugin`
    pass
