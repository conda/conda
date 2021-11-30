from ...base.context import context

from .classic import (
    Solver,
    diff_for_unlink_link_precs,
    get_pinned_specs,
    DepsModifier,
    UpdateModifier,
    Resolve,
)  # noqa
from .libmamba import LibMambaSolver


def _get_solver_logic(key=None):
    key = key or context.solver_logic.value

    # These keys match conda.base.constants.SolverLogicChoice
    return {
        "classic": Solver,
        "libmamba": LibMambaSolver,
    }[key]
