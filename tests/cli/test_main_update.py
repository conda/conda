# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from conda.exceptions import CondaUpdatePackageError
from conda.testing.integration import package_is_installed

if TYPE_CHECKING:
    from pathlib import Path

    from conda.testing.fixtures import CondaCLIFixture, TmpEnvFixture


def test_update(
    tmp_env: TmpEnvFixture,
    conda_cli: CondaCLIFixture,
    test_recipes_channel: Path,
):
    with tmp_env("versioned=1.0") as prefix:
        assert package_is_installed(prefix, "versioned=1.0")
        conda_cli("update", "versioned", f"--prefix={prefix}", "--yes")
        assert package_is_installed(prefix, "versioned=2.0")


def test_dont_update_explicit_packages(
    test_recipes_channel: Path,
    tmp_env: TmpEnvFixture,
    conda_cli: CondaCLIFixture,
):
    with tmp_env(test_recipes_channel / "noarch" / "dependent-1.0-0.tar.bz2") as prefix:
        with pytest.raises(
            CondaUpdatePackageError,
            match=r"`conda update` only supports name-only spec",
        ):
            conda_cli(
                "update",
                test_recipes_channel / "noarch" / "dependent-1.0-0.tar.bz2",
                f"--prefix={prefix}",
            )


def test_dont_update_packages_with_version_constraints(
    conda_cli: CondaCLIFixture,
    test_recipes_channel: Path,
):
    with pytest.raises(
        CondaUpdatePackageError,
        match=r"`conda update` only supports name-only spec",
    ):
        conda_cli("update", "versioned=1.0")
