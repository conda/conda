# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Collection of pytest fixtures used in conda tests."""
from __future__ import annotations

import warnings
from typing import TYPE_CHECKING, Literal, TypeVar

import py
import pytest

from ..auxlib.ish import dals
from ..base.context import conda_tests_ctxt_mgmt_def_pol, context, reset_context
from ..common.configuration import YamlRawParameter
from ..common.io import env_vars
from ..common.serialize import yaml_round_trip_load
from ..core.subdir_data import SubdirData
from ..gateways.disk.create import TemporaryDirectory

if TYPE_CHECKING:
    from typing import Iterable

    from pytest import FixtureRequest, MonkeyPatch


@pytest.fixture(autouse=True)
def suppress_resource_warning():
    """
    Suppress `Unclosed Socket Warning`

    It seems urllib3 keeps a socket open to avoid costly recreation costs.

    xref: https://github.com/kennethreitz/requests/issues/1882
    """
    warnings.filterwarnings("ignore", category=ResourceWarning)


@pytest.fixture(scope="function")
def tmpdir(tmpdir, request):
    tmpdir = TemporaryDirectory(dir=str(tmpdir))
    request.addfinalizer(tmpdir.cleanup)
    return py.path.local(tmpdir.name)


@pytest.fixture(autouse=True)
def clear_subdir_cache():
    SubdirData.clear_cached_local_channel_data()


@pytest.fixture(scope="function")
def disable_channel_notices():
    """
    Fixture that will set "context.number_channel_notices" to 0 and then set
    it back to its original value.

    This is also a good example of how to override values in the context object.
    """
    yaml_str = dals(
        """
        number_channel_notices: 0
        """
    )
    reset_context(())
    rd = {
        "testdata": YamlRawParameter.make_raw_parameters(
            "testdata", yaml_round_trip_load(yaml_str)
        )
    }
    context._set_raw_data(rd)

    yield

    reset_context(())


@pytest.fixture(scope="function")
def reset_conda_context():
    """Resets the context object after each test function is run."""
    yield

    reset_context()


@pytest.fixture()
def temp_package_cache(tmp_path_factory):
    """
    Used to isolate package or index cache from other tests.
    """
    pkgs_dir = tmp_path_factory.mktemp("pkgs")
    with env_vars(
        {"CONDA_PKGS_DIRS": str(pkgs_dir)}, stack_callback=conda_tests_ctxt_mgmt_def_pol
    ):
        yield pkgs_dir


@pytest.fixture(params=["libmamba", "classic"])
def parametrized_solver_fixture(
    request: FixtureRequest,
    monkeypatch: MonkeyPatch,
) -> Iterable[Literal["libmamba", "classic"]]:
    """
    A parameterized fixture that sets the solver backend to (1) libmamba
    and (2) classic for each test. It's using autouse=True, so only import it in
    modules that actually need it.

    Note that skips and xfails need to be done _inside_ the test body.
    Decorators can't be used because they are evaluated before the
    fixture has done its work!

    So, instead of:

        @pytest.mark.skipif(context.solver == "libmamba", reason="...")
        def test_foo():
            ...

    Do:

        def test_foo():
            if context.solver == "libmamba":
                pytest.skip("...")
            ...
    """
    yield from _solver_helper(request, monkeypatch, request.param)


@pytest.fixture
def solver_classic(
    request: FixtureRequest,
    monkeypatch: MonkeyPatch,
) -> Iterable[Literal["classic"]]:
    yield from _solver_helper(request, monkeypatch, "classic")


@pytest.fixture
def solver_libmamba(
    request: FixtureRequest,
    monkeypatch: MonkeyPatch,
) -> Iterable[Literal["libmamba"]]:
    yield from _solver_helper(request, monkeypatch, "libmamba")


Solver = TypeVar("Solver", Literal["libmamba"], Literal["classic"])


def _solver_helper(
    request: FixtureRequest,
    monkeypatch: MonkeyPatch,
    solver: Solver,
) -> Iterable[Solver]:
    # clear cached solver backends before & after each test
    context.plugin_manager.get_cached_solver_backend.cache_clear()
    request.addfinalizer(context.plugin_manager.get_cached_solver_backend.cache_clear)

    monkeypatch.setenv("CONDA_SOLVER", solver)
    reset_context()
    assert context.solver == solver

    yield solver
