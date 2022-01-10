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

from conda.base.context import context, fresh_context
from conda.core.solve.classic import Solver
from conda.core.solve.libmamba2 import LibMambaIndexHelper
from conda.core.solve.state import SolverInputState, SolverOutputState
from conda.models.match_spec import MatchSpec
from ..test_solvers import SimpleEnvironment, index_packages


def empty_prefix():
    return TemporaryDirectory(prefix="conda-test-repo-")


@pytest.fixture()
def env(solver_class=Solver) -> SimpleEnvironment:
    with empty_prefix() as prefix:
        yield SimpleEnvironment(prefix, solver_class)


@pytest.mark.parametrize(
    "default_packages",
    [
        "",
        "python,jupyter",
        "python=3",
    ],
)
def test_create_empty(default_packages):
    """
    Test what happens when `conda create` is invoked with no specs.

    `requested` is empty in that case (unless `create_default_packages` config key
    is populated, which would add specs to requested through conda.cli.install logic)
    """
    with fresh_context(CONDA_CREATE_DEFAULT_PACKAGES=default_packages), empty_prefix() as prefix:
        default_specs = [MatchSpec(spec_str) for spec_str in context.create_default_packages]
        sis = SolverInputState(prefix, requested=default_specs)
        sos = SolverOutputState(solver_input_state=sis)
        # `index` should be an IndexHelper, not None, but we don't need one for this test
        sos.prepare_specs(index=None)
        if default_packages:
            assert context.create_default_packages
        assert list(sos.real_specs.values()) == default_specs


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
    with fresh_context(CONDA_PINNED_PACKAGES=pinned):
        with empty_prefix() as prefix:
            sis = SolverInputState(prefix=prefix, requested=packages)
            sos = SolverOutputState(solver_input_state=sis)
            index = LibMambaIndexHelper()
            sos.prepare_specs(index=index)
            assert sis.pinned == {"python": MatchSpec(pinned, optional=True)}
            assert sos.real_specs == {"python": MatchSpec(pinned)}


def test_python_updates(env: SimpleEnvironment):
    """
    Usually, python is implicitly pinned to its installed major.minor version.
    That can only be overridden if the user explicitly requests python in the
    CLI specs. Ideally, the explicit spec contains a version constrain too.
    """
    # Setup the prefix
    env.repo_packages = index_packages(1)
    env.installed_packages = env.install("python 2.*", as_specs=True)
    env._write_installed_packages()

    index = LibMambaIndexHelper(installed_records=env.installed_packages)

    # If no explicit python is passed, we should see python 2.7 in the specs
    sis = SolverInputState(prefix=env._prefix_path, requested=["numpy"])
    sos = SolverOutputState(solver_input_state=sis)
    sos.prepare_specs(index)
    # First attempt, it will be pinned to the installed version
    assert sos.specs["python"] == sis.installed["python"].to_match_spec()

    # However, if we mark it as conflicting, it will be relaxed to major.minor only
    sos = SolverOutputState(solver_input_state=sis, conflicts={"python": sos.specs["python"]})
    sos.prepare_specs(index)
    assert sos.specs["python"] == MatchSpec("python=2.7")

    # If we do explicitly request it, then it won't have any version constrains
    sis = SolverInputState(prefix=env._prefix_path, requested=["python"])
    sos = SolverOutputState(solver_input_state=sis)
    sos.prepare_specs(index)
    assert ("python", MatchSpec("python")) in sos.real_specs.items()
