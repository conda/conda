# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Tests for the add_pip_as_python_dependency default-change warning."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from conda.base.context import reset_context
from conda.core.solve import Solver
from conda.models.match_spec import MatchSpec
from conda.models.records import PackageRecord

if TYPE_CHECKING:
    from pathlib import Path

    from pytest import CaptureFixture, MonkeyPatch

WARNING_SNIPPET = "add_pip_as_python_dependency defaults to true"


@pytest.mark.parametrize(
    "explicit",
    [
        pytest.param(False, id="unset-default"),
        pytest.param(True, id="explicitly-set"),
    ],
)
def test_notify_pip_as_python_deprecation(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    capsys: CaptureFixture[str],
    explicit: bool,
) -> None:
    monkeypatch.delenv("CONDA_ADD_PIP_AS_PYTHON_DEPENDENCY", raising=False)
    if explicit:
        monkeypatch.setenv("CONDA_ADD_PIP_AS_PYTHON_DEPENDENCY", "true")
    reset_context(())

    solver = Solver(str(tmp_path), specs_to_add=(MatchSpec("python"),))
    link_precs = (
        PackageRecord(name="python", version="3.12.0", build="0", build_number=0),
        PackageRecord(name="pip", version="24.0", build="0", build_number=0),
    )
    solver._notify_pip_as_python_deprecation(link_precs)

    err = capsys.readouterr().err
    if explicit:
        assert WARNING_SNIPPET not in err
    else:
        assert WARNING_SNIPPET in err
