# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (C) 2022 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
# this is where we simulate an ImportError
# tested in test_manager.py::test_load_entrypoints_importerror
import package_that_does_not_exist

from conda import plugins
from conda.core.solve import Solver


@plugins.hookimpl
def conda_solvers():
    """The conda plugin hook implementation to load the solver into conda."""
    yield plugins.CondaSolver(
        name="test",
        backend=Solver,
    )
