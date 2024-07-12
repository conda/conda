# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from conda.base.context import context
from conda.exceptions import UnsatisfiableError
from conda.models.match_spec import MatchSpec
from conda.testing import CondaCLIFixture, PathFactoryFixture, TmpEnvFixture

pytestmark = pytest.mark.usefixtures("parametrized_solver_fixture")


@pytest.mark.integration
def test_pre_link_message(
    test_recipes_channel: Path,
    mocker: MockerFixture,
    tmp_env: TmpEnvFixture,
    conda_cli: CondaCLIFixture,
):
    mocker.patch("conda.cli.common.confirm_yn", return_value=True)

    with tmp_env() as prefix:
        stdout, _, _ = conda_cli(
            "install",
            *("--prefix", prefix),
            "pre_link_messages_package",
            "--yes",
        )
        assert "Lorem ipsum dolor sit amet" in stdout


@pytest.mark.integration
def test_find_conflicts_called_once(
    mocker: MockerFixture,
    tmp_env: TmpEnvFixture,
    path_factory: PathFactoryFixture,
    conda_cli: CondaCLIFixture,
):
    if context.solver == "libmamba":
        pytest.skip("conda-libmamba-solver handles conflicts differently")

    bad_deps = {
        "python": {
            (
                (
                    MatchSpec("statistics"),
                    MatchSpec("python[version='>=2.7,<2.8.0a0']"),
                ),
                "python=3",
            )
        }
    }
    mocked_find_conflicts = mocker.patch(
        "conda.resolve.Resolve.find_conflicts",
        side_effect=UnsatisfiableError(bad_deps, strict=True),
    )
    channels = (
        "--repodata-fn",
        "current_repodata.json",
        "--override-channels",
        "-c",
        "defaults",
    )
    with tmp_env("python=3.9", *channels) as prefix:
        with pytest.raises(UnsatisfiableError):
            # Statistics is a py27 only package allowing us a simple unsatisfiable case
            conda_cli("install", f"--prefix={prefix}", "statistics", "--yes", *channels)
        assert mocked_find_conflicts.call_count == 1

        with pytest.raises(UnsatisfiableError):
            conda_cli(
                "install",
                f"--prefix={prefix}",
                "statistics",
                "--freeze-installed",
                "--yes",
                *channels,
            )
        assert mocked_find_conflicts.call_count == 2

    with pytest.raises(UnsatisfiableError):
        # statistics seems to be available on 3.10 though
        conda_cli(
            "create",
            f"--prefix={path_factory()}",
            "statistics",
            "python=3.9",
            "--yes",
            *channels,
        )
    assert mocked_find_conflicts.call_count == 3



@pytest.mark.integration
def test_emscripten_forge(
    test_recipes_channel: Path,
    mocker: MockerFixture,
    tmp_env: TmpEnvFixture,
    conda_cli: CondaCLIFixture,
):
    mocker.patch("conda.cli.common.confirm_yn", return_value=True)

    with tmp_env() as prefix:
        stdout, _, _ = conda_cli(
            "create","--platform=emscripten-32",f"--prefix={prefix}","--yes","--override-channels","-c","https://repo.mamba.pm/emscripten-forge","-c","conda-forge","pyjs"
        )
        