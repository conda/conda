# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import warnings
from typing import TYPE_CHECKING

import pytest

from conda.base.context import context, reset_context
from conda.core.solve import Solver
from conda.deprecations import DeprecationHandler
from conda.models.match_spec import MatchSpec
from conda.models.records import PackageRecord

if TYPE_CHECKING:
    from pathlib import Path

    from pytest import MonkeyPatch
    from pytest_mock import MockerFixture


@pytest.mark.parametrize(
    "version,warning",
    [
        ("26.9.0", PendingDeprecationWarning),
        ("26.10.0", PendingDeprecationWarning),
        ("27.3.0", FutureWarning),
    ],
)
@pytest.mark.parametrize(
    "configured,requested_pip",
    [(None, False), ("true", False), ("false", False), (None, True)],
)
def test_notify_pip_as_python_deprecation(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    mocker: MockerFixture,
    version: str,
    warning: type[Warning],
    configured: str | None,
    requested_pip: bool,
) -> None:
    monkeypatch.delenv("CONDA_ADD_PIP_AS_PYTHON_DEPENDENCY", raising=False)
    if configured is not None:
        monkeypatch.setenv("CONDA_ADD_PIP_AS_PYTHON_DEPENDENCY", configured)
    monkeypatch.setenv("CONDA_QUIET", "false")
    monkeypatch.setenv("CONDA_JSON", "false")
    reset_context(())
    mocker.patch("conda.core.solve.deprecated", DeprecationHandler(version))

    specs = (MatchSpec("python"),)
    if requested_pip:
        specs += (MatchSpec("pip"),)
    solver = Solver(str(tmp_path), specs_to_add=specs)
    link_precs = tuple(
        PackageRecord(name=name, version="1.0", build="0", build_number=0)
        for name in ("python", "pip")
    )

    if configured is None and not requested_pip:
        # Exercise the suite's warning filters before capturing the notice.
        solver._notify_pip_as_python_deprecation(link_precs)

        with pytest.warns(
            warning, match="^Implicit installation of pip as a Python dependency"
        ) as caught:
            solver._notify_pip_as_python_deprecation(link_precs)

        assert len(caught) == 1
        message = str(caught[0].message)
        assert "This default will change to false in conda 27.9.0." in message
        assert "conda config --set add_pip_as_python_dependency true" in message
        assert "add_pip_as_python_dependency=true is deprecated" not in message
    else:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            solver._notify_pip_as_python_deprecation(link_precs)

        assert not caught


@pytest.mark.parametrize("link_names", [(), ("python", "pip")])
def test_notify_pip_as_python_deprecation_with_expanded_ssl_verify(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    mocker: MockerFixture,
    link_names: tuple[str, ...],
) -> None:
    ca_bundle = tmp_path / "ca-bundle.pem"
    ca_bundle.touch()
    condarc = tmp_path / "condarc"
    condarc.write_text("ssl_verify: $REVIEW_CA_BUNDLE\n")
    monkeypatch.setenv("REVIEW_CA_BUNDLE", str(ca_bundle))
    monkeypatch.delenv("CONDA_SSL_VERIFY", raising=False)
    monkeypatch.delenv("CONDA_ADD_PIP_AS_PYTHON_DEPENDENCY", raising=False)
    monkeypatch.setenv("CONDA_QUIET", "false")
    monkeypatch.setenv("CONDA_JSON", "false")
    reset_context((str(condarc),))
    mocker.patch("conda.core.solve.deprecated", DeprecationHandler("27.3.0"))
    assert context.ssl_verify == str(ca_bundle)

    solver = Solver(str(tmp_path), specs_to_add=(MatchSpec("python"),))
    link_precs = tuple(
        PackageRecord(name=name, version="1.0", build="0", build_number=0)
        for name in link_names
    )

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        solver._notify_pip_as_python_deprecation(link_precs)

    assert len(caught) == bool(link_names)
    if caught:
        assert caught[0].category is FutureWarning
