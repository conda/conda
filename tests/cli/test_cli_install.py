# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from conda.base.context import context, reset_context
from conda.core.prefix_data import PrefixData
from conda.exceptions import DryRunExit, EnvironmentIsFrozenError, UnsatisfiableError
from conda.models.match_spec import MatchSpec
from conda.testing.integration import package_is_installed

if TYPE_CHECKING:
    from pathlib import Path

    from pytest import MonkeyPatch
    from pytest_mock import MockerFixture

    from conda.testing.fixtures import (
        CondaCLIFixture,
        PathFactoryFixture,
        TmpEnvFixture,
    )


pytestmark = pytest.mark.usefixtures("parametrized_solver_fixture")


@pytest.mark.integration
def test_pre_link_message(
    test_recipes_channel: Path,
    mocker: MockerFixture,
    tmp_env: TmpEnvFixture,
    conda_cli: CondaCLIFixture,
):
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
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    tmp_env: TmpEnvFixture,
):
    monkeypatch.setenv("CONDA_PKGS_DIRS", str(tmp_path))
    reset_context()

    with tmp_env(
        "--platform=emscripten-wasm32",
        "--override-channels",
        "-c",
        "https://repo.mamba.pm/emscripten-forge",
        "-c",
        "conda-forge",
        "pyjs",
    ) as prefix:
        assert package_is_installed(prefix, "pyjs")


def test_frozen_env_cep22(tmp_env, conda_cli, monkeypatch):
    with tmp_env("ca-certificates") as prefix:
        prefix_data = PrefixData(prefix)
        prefix_data._frozen_file.touch()
        assert prefix_data.is_frozen()

        # No message
        conda_cli("install", "-p", prefix, "zlib", raises=EnvironmentIsFrozenError)
        conda_cli(
            "remove", "-p", prefix, "ca-certificates", raises=EnvironmentIsFrozenError
        )
        conda_cli(
            "update", "-p", prefix, "ca-certificates", raises=EnvironmentIsFrozenError
        )

        # Bypass protection with CLI flag
        conda_cli(
            "install",
            "-p",
            prefix,
            "zlib",
            "--dry-run",
            "--override-frozen",
            raises=DryRunExit,
        )
        conda_cli(
            "remove",
            "-p",
            prefix,
            "ca-certificates",
            "--dry-run",
            "--override-frozen",
            raises=DryRunExit,
        )
        out, err, rc = conda_cli(
            "update",
            "-p",
            prefix,
            "ca-certificates",
            "--dry-run",
            "--override-frozen",
        )
        assert rc == 0

        # Bypass protection with env var
        with monkeypatch.context() as monkeyctx:
            monkeyctx.setenv("CONDA_PROTECT_FROZEN_ENVS", "0")
            conda_cli(
                "install",
                "-p",
                prefix,
                "zlib",
                "--dry-run",
                raises=DryRunExit,
            )
            conda_cli(
                "remove",
                "-p",
                prefix,
                "ca-certificates",
                "--dry-run",
                raises=DryRunExit,
            )
            out, err, rc = conda_cli(
                "update",
                "-p",
                prefix,
                "ca-certificates",
                "--dry-run",
            )
            assert rc == 0

        # With message
        prefix_data._frozen_file.write_text('{"message": "EnvOnTheRocks"}')
        out, err, exc = conda_cli(
            "install",
            "-p",
            prefix,
            "zlib",
            raises=EnvironmentIsFrozenError,
        )
        assert "EnvOnTheRocks" in str(exc)
        out, err, exc = conda_cli(
            "remove",
            "-p",
            prefix,
            "ca-certificates",
            raises=EnvironmentIsFrozenError,
        )
        assert "EnvOnTheRocks" in str(exc)
        out, err, exc = conda_cli(
            "update",
            "-p",
            prefix,
            "ca-certificates",
            raises=EnvironmentIsFrozenError,
        )
        assert "EnvOnTheRocks" in str(exc)

        prefix_data._frozen_file.unlink()
        conda_cli("install", "-p", prefix, "zlib", "--dry-run", raises=DryRunExit)
        conda_cli(
            "remove", "-p", prefix, "ca-certificates", "--dry-run", raises=DryRunExit
        )
        out, err, rc = conda_cli("update", "-p", prefix, "ca-certificates", "--dry-run")
        assert rc == 0
