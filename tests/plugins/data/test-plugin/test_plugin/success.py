# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
# see tests.plugins.test_manager.test_load_entrypoints_success
# simulate a successful plugin
from conda import plugins
from conda.core.solve import Solver


@plugins.hookimpl
def conda_solvers():
    """The conda plugin hook implementation to load the solver into conda."""
    yield plugins.CondaSolver(
        name="test",
        backend=Solver,
    )
