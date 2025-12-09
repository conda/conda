# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import os
import stat
import uuid
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from conda.auxlib.ish import dals
from conda.common.compat import on_win
from conda.exceptions import (
    DirectoryNotACondaEnvironmentError,
    EnvironmentLocationNotFound,
)
from conda.testing.integration import env_or_set, which_or_where

if TYPE_CHECKING:
    from conda.testing.fixtures import CondaCLIFixture, TmpEnvFixture


def test_run_returns_int(tmp_env: TmpEnvFixture, conda_cli: CondaCLIFixture):
    with tmp_env() as prefix:
        stdout, stderr, err = conda_cli("run", f"--prefix={prefix}", "echo", "hi")

        assert stdout.strip() == "hi"
        assert not stderr
        assert isinstance(err, int)


def test_run_returns_zero_errorlevel(
    tmp_env: TmpEnvFixture,
    conda_cli: CondaCLIFixture,
):
    with tmp_env() as prefix:
        stdout, stderr, err = conda_cli("run", f"--prefix={prefix}", "exit", "0")

        assert not stdout
        assert not stderr
        assert not err


def test_run_returns_nonzero_errorlevel(
    tmp_env: TmpEnvFixture,
    conda_cli: CondaCLIFixture,
):
    with tmp_env() as prefix:
        stdout, stderr, err = conda_cli("run", f"--prefix={prefix}", "exit", "5")

        assert not stdout
        assert stderr
        assert err == 5


@pytest.mark.parametrize("flag", ["--no-capture-output", "-s"])
def test_run_uncaptured(
    tmp_env: TmpEnvFixture,
    conda_cli: CondaCLIFixture,
    flag: str,
):
    with tmp_env() as prefix:
        random_text = uuid.uuid4().hex
        stdout, stderr, err = conda_cli(
            "run",
            f"--prefix={prefix}",
            flag,
            *("echo", random_text),
        )

        assert not stdout
        assert not stderr
        assert not err


@pytest.mark.skipif(on_win, reason="cannot make readonly env on win")
def test_run_readonly_env(tmp_env: TmpEnvFixture, conda_cli: CondaCLIFixture):
    with tmp_env() as prefix:
        # Remove write permissions
        current = stat.S_IMODE(os.lstat(prefix).st_mode)
        os.chmod(prefix, current & ~stat.S_IWRITE)

        # Confirm we do not have write access
        with pytest.raises(PermissionError):
            Path(prefix, "test.txt").open("w+")

        stdout, stderr, err = conda_cli("run", f"--prefix={prefix}", "exit", "0")

        assert not stdout
        assert not stderr
        assert not err


def test_conda_run_nonexistent_prefix(tmp_path: Path, conda_cli: CondaCLIFixture):
    with pytest.raises(EnvironmentLocationNotFound):
        conda_cli("run", f"--prefix={tmp_path / 'missing'}", "echo", "hello")


def test_conda_run_prefix_not_a_conda_env(tmp_path: Path, conda_cli: CondaCLIFixture):
    with pytest.raises(DirectoryNotACondaEnvironmentError):
        conda_cli("run", f"--prefix={tmp_path}", "echo", "hello")


def test_multiline_run_command(tmp_env: TmpEnvFixture, conda_cli: CondaCLIFixture):
    with tmp_env() as prefix:
        stdout, stderr, _ = conda_cli(
            "run",
            f"--prefix={prefix}",
            f"--cwd={prefix}",
            dals(
                f"""
                {env_or_set}
                {which_or_where} conda
                """
            ),
        )
        assert stdout
        assert not stderr


def test_run_with_separator(
    test_recipes_channel: Path,
    tmp_env: TmpEnvFixture,
    conda_cli: CondaCLIFixture,
):
    with tmp_env("small-executable") as prefix:
        stdout, stderr, err = conda_cli(
            "run",
            f"--prefix={prefix}",
            "--",
            "small",
            "-v",
            "-c",
            "spam",
        )

        assert "-v" in stdout
        assert "-c" in stdout
        assert "spam" in stdout
        assert not err


def test_run_with_separator_multiple_v_flags(
    test_recipes_channel: Path,
    tmp_env: TmpEnvFixture,
    conda_cli: CondaCLIFixture,
):
    with tmp_env("small-executable") as prefix:
        stdout, stderr, err = conda_cli(
            "run",
            f"--prefix={prefix}",
            "--",
            "small",
            "-vvv",
            "-c",
            "eggs",
        )

        assert "-vvv" in stdout
        assert "-c" in stdout
        assert "eggs" in stdout
        assert not err


def test_run_with_separator_combined_options(
    test_recipes_channel: Path,
    tmp_env: TmpEnvFixture,
    conda_cli: CondaCLIFixture,
):
    with tmp_env("small-executable") as prefix:
        stdout, stderr, err = conda_cli(
            "run",
            f"--prefix={prefix}",
            "--",
            "small",
            "--vic",
            "60",
        )

        assert "--vic" in stdout
        assert "60" in stdout
        assert not err


def test_run_without_separator(
    test_recipes_channel: Path,
    tmp_env: TmpEnvFixture,
    conda_cli: CondaCLIFixture,
):
    with tmp_env("small-executable") as prefix:
        stdout, stderr, err = conda_cli(
            "run",
            f"--prefix={prefix}",
            "small",
            "--version",
        )

        assert "--version" in stdout
        assert not err


def test_run_if_separator_not_at_start(
    tmp_env: TmpEnvFixture,
    conda_cli: CondaCLIFixture,
):
    with tmp_env() as prefix:
        stdout, stderr, err = conda_cli(
            "run",
            f"--prefix={prefix}",
            "echo",
            "--",
            "hello",
        )
        assert "-- hello" in stdout
        assert not err


def test_run_with_empty_command_will_raise(
    conda_cli: CondaCLIFixture,
):
    from conda.exceptions import ArgumentError

    with pytest.raises(ArgumentError, match="No command specified"):
        conda_cli("run")
