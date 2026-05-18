# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from argparse import Namespace
from typing import TYPE_CHECKING

import pytest

from conda.base.context import context, reset_context
from conda.cli.install import reinstall_packages
from conda.core.prefix_data import PrefixData
from conda.exceptions import DryRunExit, EnvironmentIsFrozenError, UnsatisfiableError
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
    test_recipes_channel: Path,
    mocker: MockerFixture,
    tmp_env: TmpEnvFixture,
    path_factory: PathFactoryFixture,
    conda_cli: CondaCLIFixture,
):
    if context.solver in ("libmamba", "rattler"):
        pytest.skip(f"conda-{context.solver}-solver handle conflicts differently")

    # Side effect only needs to be UnsatisfiableError; dependency structure is irrelevant.
    mocked_find_conflicts = mocker.patch(
        "conda.resolve.Resolve.find_conflicts",
        side_effect=UnsatisfiableError([], strict=True),
    )
    with tmp_env("versioned=2.0") as prefix:
        with pytest.raises(UnsatisfiableError):
            conda_cli("install", f"--prefix={prefix}", "unsatisfiable")
        assert mocked_find_conflicts.call_count == 1

        with pytest.raises(UnsatisfiableError):
            conda_cli(
                "install",
                f"--prefix={prefix}",
                "unsatisfiable",
                "--freeze-installed",
            )
        assert mocked_find_conflicts.call_count == 2

    with pytest.raises(UnsatisfiableError):
        conda_cli(
            "create",
            f"--prefix={path_factory()}",
            "versioned=1.0",
            "unsatisfiable",
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
        "https://repo.prefix.dev/emscripten-forge-4x",
        "-c",
        "https://repo.prefix.dev/conda-forge",
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


def test_reinstall_packages_calls_install(tmp_path: Path, mocker: MockerFixture):
    """Test that reinstall_packages correctly calls install() with parser argument.

    This is a regression test for #15669 where reinstall_packages() was calling
    install(args) without the required parser argument, causing conda doctor --fix
    to fail with: "install() missing 1 required positional argument: 'parser'"
    """
    # Mock install to verify it's called with correct arguments
    mock_install = mocker.patch("conda.cli.install.install", return_value=0)

    # Create minimal args namespace with required attributes
    args = Namespace(
        prefix=str(tmp_path),
        name=None,
    )

    # This would fail without the fix:
    # TypeError: install() missing 1 required positional argument: 'parser'
    result = reinstall_packages(args, ["some-package"], force_reinstall=True)

    assert result == 0
    mock_install.assert_called_once()

    # Verify install was called with at least 2 positional arguments (args, parser)
    call_args = mock_install.call_args
    assert call_args[0][0] is args  # First positional arg is args
    assert len(call_args[0]) >= 2  # Must have at least 2 positional args


def test_reinstall_args(tmp_path: Path, mocker: MockerFixture):
    """Test that reinstall_packages includes all required arguments when calling install."""

    class EmptySolver:
        def __init__(self, *args, **kwargs):
            pass

        def solve_for_transaction(self, *args, **kwargs):
            pass

    mock_solver = mocker.patch(
        "conda.cli.install.context.plugin_manager.get_cached_solver_backend",
        return_value=EmptySolver,
    )
    mock_handle_txn = mocker.patch("conda.cli.install.handle_txn", return_value=0)

    # Create minimal args namespace with required attributes
    args = Namespace(prefix=str(tmp_path), name=None, cmd="install")

    reinstall_packages(args, ["some-package"], force_reinstall=True)
    mock_solver.assert_called_once()
    mock_handle_txn.assert_called_once()
