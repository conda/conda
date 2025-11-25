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
):
    with tmp_env("python==3.10") as prefix:
        assert package_is_installed(prefix, "python==3.10")
        conda_cli("update", "python", "--prefix", prefix, "--yes")
        assert package_is_installed(prefix, "python>3.10")


def test_dont_update_explicit_packages(
    test_recipes_channel: Path,
    tmp_env: TmpEnvFixture,
    conda_cli: CondaCLIFixture,
):
    with tmp_env(test_recipes_channel / "noarch" / "dependent-1.0-0.tar.bz2") as prefix:
        with pytest.raises(CondaUpdatePackageError) as excinfo:
            conda_cli(
                "update",
                test_recipes_channel / "noarch" / "dependent-1.0-0.tar.bz2",
                "--prefix",
                prefix,
            )
        assert "`conda update` only supports name-only spec" in excinfo.value.message


def test_dont_update_packages_with_version_constraints(
    conda_cli: CondaCLIFixture,
):
    with pytest.raises(CondaUpdatePackageError) as excinfo:
        conda_cli(
            "update",
            "python=3.10",
        )
    assert "`conda update` only supports name-only spec" in excinfo.value.message
