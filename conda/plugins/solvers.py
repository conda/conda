# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from functools import lru_cache

from . import hookimpl, CondaSolver
from ..auxlib.ish import dals
from ..base.constants import CLASSIC_SOLVER
from ..common.io import dashlist
from ..exceptions import PluginError


@hookimpl(tryfirst=True)  # make sure the classic solver can't be overwritten
def conda_solvers():
    """
    The classic solver as shipped by default in conda.
    """
    from ..core.solve import Solver

    yield CondaSolver(
        name=CLASSIC_SOLVER,
        backend=Solver,
    )


# FUTURE: Python 3.8+, replace with functools.cached_property
@lru_cache(maxsize=None)
def get_available_solvers(pm):
    """
    Given the provided plugin manager, return all registered solvers.
    """
    solvers = sorted(
        (
            solver
            for solvers in pm.hook.conda_solvers()
            for solver in solvers
        ),
        key=lambda solver: solver.name,
    )
    # Check for conflicts
    seen = set()
    conflicts = [
        solver
        for solver in solvers
        if solver.name in seen or seen.add(solver.name)
    ]
    if conflicts:
        raise PluginError(
            dals(
                f"""
                Conflicting entries found for the following solvers:
                {dashlist(conflicts)}
                Multiple conda plugins are registering these solvers via the
                `conda_solvers` hook; please make sure that
                you do not have any incompatible plugins installed.
                """
            )
        )
    return solvers
