# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from conda.testing.integration import package_is_installed

if TYPE_CHECKING:
    from pathlib import Path

    from pytest import MonkeyPatch

    from conda.testing.fixtures import CondaCLIFixture, TmpChannelFixture, TmpEnvFixture

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
    clear_cache: None,
    test_recipes_channel: Path,
    tmp_channel: TmpChannelFixture,
    mock_channels: list[str],
):
    package1 = "versioned"
    package2 = "dependent"  # with transitive dependency
    package3 = "dependency"

    # set pinned package
    if pinned_package:
        monkeypatch.setenv("CONDA_PINNED_PACKAGES", f"{package1}=1")

    # create a temporary channel with older versions of the packages
    with tmp_channel(f"{package1}=1", f"{package2}=1") as (
        old_recipes_path,
        old_recipes_channel,
    ):
        mock_channels[:] = [old_recipes_channel]

        # create environment with package1 and package2
        with tmp_env(package1, package2) as prefix:
            # check both packages are installed from old_recipes_channel
            assert (
                package_is_installed(prefix, f"{package1}=1").channel.name
                == package_is_installed(prefix, f"{package2}=1").channel.name
                == package_is_installed(prefix, f"{package3}=1").channel.name
                == old_recipes_path.name
            )

            # update --all using the new channel
            mock_channels[:] = [str(test_recipes_channel)]
            conda_cli("update", f"--prefix={prefix}", "--all", "--yes")

            # check pinned package is unchanged but unpinned packages are updated from test_recipes_channel
            version = "1" if pinned_package else "2"
            channel = old_recipes_path if pinned_package else test_recipes_channel
            assert (
                package_is_installed(prefix, f"{package1}={version}").channel.name
                == channel.name
            )
            assert (
                package_is_installed(prefix, f"{package2}=2").channel.name
                == package_is_installed(prefix, f"{package3}=2").channel.name
                == test_recipes_channel.name
            )
