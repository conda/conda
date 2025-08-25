# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from conda.base.context import reset_context

if TYPE_CHECKING:
    from pathlib import Path

    from pytest import MonkeyPatch

    from conda.testing.fixtures import CondaCLIFixture


def test_create_default_packages_can_not_be_explicit(
    monkeypatch: MonkeyPatch,
    conda_cli: CondaCLIFixture,
    tmp_path: Path,
):
    monkeypatch.setenv(
        "CONDA_CREATE_DEFAULT_PACKAGES",
        (url := "https://repo.anaconda.com/pkgs/main/linux-64/ca-certificates-2025.2.25-h06a4308_0.conda"),
    )
    reset_context()
    with pytest.warns(UserWarning, match=rf"Ignoring invalid packages.+{url}"):
        conda_cli("create", "--prefix", tmp_path, "--yes")

        assert (
            "Ignoring invalid packages in `create_default_packages`: \n  - https://repo.anaconda.com/pkgs/main/linux-64/ca-certificates-2025.2.25-h06a4308_0.conda\n\nExplicit package are not allowed, use package names like 'numpy' or specs like 'numpy>=1.20' instead.\nTry using the command `conda config --show-sources` to verify your conda configuration.\n"
            in [str(warn.message) for warn in warning]
        )
