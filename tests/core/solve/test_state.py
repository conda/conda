"""
Test the Solver API helpers. These objects are solver-agnostic
but encode most of the logic needed to expose a prefix state,
command line flags and context environment variables to the solver
itself.

We'll try our best to encode the intricate legacy logic as a testable
behavioral units that, eventually, will allow us to further split the
logic into discrete, composable parts.
"""
from tempfile import TemporaryDirectory

import pytest

from conda.base.context import context, reset_context
from conda.common.io import env_var
from conda.core.solve.classic import Solver
from conda.core.solve.libmamba2 import LibMambaIndexHelper
from conda.core.solve.state import SolverInputState, SolverOutputState
from conda.models.match_spec import MatchSpec
from ...test_solvers import SimpleEnvironment


def empty_prefix():
    return TemporaryDirectory(prefix="conda-test-repo-")


@pytest.fixture()
def env(solver_class=Solver):
    with empty_prefix() as prefix:
        yield SimpleEnvironment(prefix, solver_class)


@pytest.mark.parametrize(
    "default_packages",
    [
        "",
        # TODO: These will fail
        # "python",
        # "python,jupyter",
        # "python=3",
    ],
)
def test_create_empty(default_packages):
    with env_var("CONDA_CREATE_DEFAULT_PACKAGES", default_packages):
        reset_context()
        with empty_prefix() as prefix:
            sis = SolverInputState(prefix)
            sos = SolverOutputState(solver_input_state=sis)
            # `index` should be an IndexHelper, not None, but we don't need one for this test
            sos.prepare_specs(index=None)
            if default_packages:
                assert context.create_default_packages
            assert tuple(sos.real_specs.values()) == context.create_default_packages


@pytest.mark.parametrize("packages", [["python"], ["conda"]])
def test_create_one_package(packages):
    with empty_prefix() as prefix:
        sis = SolverInputState(prefix=prefix, requested=packages)
        sos = SolverOutputState(solver_input_state=sis)
        # `index` should be an IndexHelper, not None, but we don't need one for this test
        sos.prepare_specs(index=None)
        expected = {name: MatchSpec(name) for name in packages}
        assert sos.real_specs == expected


def test_create_requested_and_pinned():
    """
    Unclear what this test should cover. First pass (no conflicts),
    allows pinned to take precedence over requested.
    """
    packages = ("python",)
    pinned = "python=3"
    with env_var("CONDA_PINNED_PACKAGES", pinned):
        reset_context()
        with empty_prefix() as prefix:
            sis = SolverInputState(prefix=prefix, requested=packages)
            sos = SolverOutputState(solver_input_state=sis)
            index = LibMambaIndexHelper()
            sos.prepare_specs(index=index)
            assert sis.pinned == {"python": MatchSpec(pinned, optional=True)}
            assert sos.real_specs == {"python": MatchSpec(pinned)}


def test_update_major_python(env):
    pass
