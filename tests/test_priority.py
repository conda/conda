# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from conda.core.prefix_data import PrefixData

if TYPE_CHECKING:
    from pytest import MonkeyPatch

    from conda.testing.fixtures import CondaCLIFixture, TmpEnvFixture

pytestmark = pytest.mark.usefixtures("parametrized_solver_fixture")


@pytest.mark.integration
@pytest.mark.parametrize(
    "pinned_package",
    [
        pytest.param(True, id="with pinned_package"),
        pytest.param(False, id="without pinned_package"),
    ],
)
def test_reorder_channel_priority(
    tmp_env: TmpEnvFixture,
    monkeypatch: MonkeyPatch,
    conda_cli: CondaCLIFixture,
    pinned_package: bool,
    clear_conda_session_cache: None,
):
    # use "cheap" packages with no dependencies
    package2 = "zlib"
    package1 = "xz"

    # set pinned package
    if pinned_package:
        monkeypatch.setenv("CONDA_PINNED_PACKAGES", package1)

    # create environment with package1 and package2
    with tmp_env(
        "--override-channels", "--channel=defaults", package1, package2
    ) as prefix:
        # check both packages are installed from defaults
        PrefixData._cache_.clear()
        assert PrefixData(prefix).get(package1).channel.name == "pkgs/main"
        assert PrefixData(prefix).get(package2).channel.name == "pkgs/main"

        # update --all
        conda_cli(
            "update",
            f"--prefix={prefix}",
            "--override-channels",
            "--channel=conda-forge",
            "--all",
            "--yes",
        )
        # check pinned package is unchanged but unpinned packages are updated from conda-forge
        PrefixData._cache_.clear()
        expected_channel = "pkgs/main" if pinned_package else "conda-forge"
        assert PrefixData(prefix).get(package1).channel.name == expected_channel
        assert PrefixData(prefix).get(package2).channel.name == "conda-forge"

        # Check that oher transient deps do change
        assert PrefixData(prefix).get("libzlib").channel.name == "conda-forge"
