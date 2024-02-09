# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from conda.core.solve import Solver
from conda.testing.solver_helpers import SolverTests


class TestClassicSolver(SolverTests):
    @property
    def solver_class(self) -> type[Solver]:
        return Solver


class TestLibMambaSolver(SolverTests):
    @property
    def solver_class(self) -> type[Solver]:
        from conda_libmamba_solver.solver import LibMambaSolver

        return LibMambaSolver

    @property
    def tests_to_skip(self):
        return {
            "conda-libmamba-solver does not support features": [
                "test_iopro_mkl",
                "test_iopro_nomkl",
                "test_mkl",
                "test_accelerate",
                "test_scipy_mkl",
                "test_pseudo_boolean",
                "test_no_features",
                "test_surplus_features_1",
                "test_surplus_features_2",
                "test_remove",
                # this one below only fails reliably on windows;
                # it passes Linux on CI, but not locally?
                "test_unintentional_feature_downgrade",
            ],
        }


@pytest.mark.parametrize("solver", ("classic", "libmamba"))
def test_remove_globbed_package_names(solver):
    "https://github.com/conda/conda-libmamba-solver/issues/434"
    with make_temp_env("zlib", "ca-certificates") as prefix:
        process = conda_subprocess(
            "remove",
            "--yes",
            f"--prefix={prefix}",
            "*lib*",
            "--dry-run",
            "--json",
            f"--solver={solver}",
        )
        print(process.stdout)
        print(process.stderr, file=sys.stderr)
        assert process.returncode == 0
        data = json.loads(process.stdout)
        assert data.get("success")
        assert any(pkg["name"] == "zlib" for pkg in data["actions"]["UNLINK"])
        if "LINK" in data["actions"]:
            assert all(pkg["name"] != "zlib" for pkg in data["actions"]["LINK"])
        # if ca-certificates is in the unlink list, it should also be in the link list (reinstall)
        for package in data["actions"]["UNLINK"]:
            if package["name"] == "ca-certificates":
                assert any(pkg["name"] == "ca-certificates" for pkg in data["actions"]["LINK"])
