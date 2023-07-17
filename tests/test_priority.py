# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import pytest
from pytest import MonkeyPatch
from pytest_mock import MockerFixture

from conda.base.context import context, reset_context
from conda.core.prefix_data import PrefixData
from conda.testing import CondaCLIFixture, TmpEnvFixture
from conda.testing.helpers import set_active_prefix


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
    mocker: MockerFixture,
    conda_cli: CondaCLIFixture,
    pinned_package: bool,
):
    # use "cheap" packages with no dependencies
    package1 = "zlib"
    package2 = "ca-certificates"

    # set pinned package
    if pinned_package:
        monkeypatch.setenv("CONDA_PINNED_PACKAGES", package1)

    # add defaults channel
    monkeypatch.setenv("CONDA_CHANNELS", "defaults")
    reset_context()
    assert context.channels == ("defaults",)

    # create environment with package1 and package2
    with tmp_env(package1, package2) as prefix, set_active_prefix(prefix):
        # check both packages are installed from defaults
        PrefixData._cache_.clear()
        assert PrefixData(prefix).get(package1).channel.name == "pkgs/main"
        assert PrefixData(prefix).get(package2).channel.name == "pkgs/main"

        # add conda-forge channel
        monkeypatch.setenv("CONDA_CHANNELS", "conda-forge,defaults")
        reset_context()
        assert context.channels == ("conda-forge", "defaults")

        # update --all
        conda_cli("update", "--prefix", prefix, "--all", "--yes")

        # check pinned package is unchanged but unpinned packages are updated from conda-forge
        PrefixData._cache_.clear()
        expected_channel = "pkgs/main" if pinned_package else "conda-forge"
        assert PrefixData(prefix).get(package1).channel.name == expected_channel
        assert PrefixData(prefix).get(package2).channel.name == "conda-forge"
