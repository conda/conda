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
from conda.base.context import context
from conda.common.compat import on_win
from conda.exceptions import (
    DirectoryNotACondaEnvironmentError,
    EnvironmentLocationNotFound,
)
from conda.testing.integration import env_or_set, which_or_where
from conda.utils import wrap_subprocess_call

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


def test_conda_run_nonexistant_prefix(tmp_path: Path, conda_cli: CondaCLIFixture):
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


@pytest.mark.skipif(not on_win, reason="Windows-specific test")
def test_run_deactivates_environment_windows(
    request: pytest.FixtureRequest,
    tmp_env: TmpEnvFixture,
    monkeypatch: pytest.MonkeyPatch,
):
    # Set env var to prevent script deletion, so we can inspect it.
    monkeypatch.setenv("CONDA_TEST_SAVE_TEMPS", "1")

    with tmp_env() as prefix:
        script_path, _ = wrap_subprocess_call(
            root_prefix=context.root_prefix,
            prefix=str(prefix),
            dev_mode=False,
            debug_wrapper_scripts=False,
            arguments=["echo", "test"],
            use_system_tmp_path=True,
        )

        request.addfinalizer(lambda: Path(script_path).unlink(missing_ok=True))

        script_content = Path(script_path).read_text()
        lines = script_content.split("\n")

        assert "deactivate.d" in script_content, (
            "Windows wrapper script should check for deactivation scripts"
        )

        echo_line_idx = None
        deactivate_check_idx = None

        for idx, line in enumerate(lines):
            if "echo" in line and "test" in line:
                echo_line_idx = idx
            if "deactivate.d" in line and "EXIST" in line:
                deactivate_check_idx = idx

        assert deactivate_check_idx is not None, (
            "Could not find deactivate.d directory check in the Windows wrapper script"
        )
        assert echo_line_idx is not None, (
            "Could not find the user's command in the Windows wrapper script"
        )
        # Verify deactivation check comes after the user's command
        assert deactivate_check_idx > echo_line_idx, (
            "On Windows, deactivation check should come after the user's command"
        )


@pytest.mark.skipif(on_win, reason="Unix-specific test")
def test_run_deactivates_environment_unix(
    request: pytest.FixtureRequest,
    tmp_env: TmpEnvFixture,
    monkeypatch: pytest.MonkeyPatch,
):
    # Set env var to prevent script deletion, so we can inspect it.
    monkeypatch.setenv("CONDA_TEST_SAVE_TEMPS", "1")

    with tmp_env() as prefix:
        script_path, _ = wrap_subprocess_call(
            root_prefix=context.root_prefix,
            prefix=str(prefix),
            dev_mode=False,
            debug_wrapper_scripts=False,
            arguments=["echo", "test"],
            use_system_tmp_path=True,
        )

        request.addfinalizer(lambda: Path(script_path).unlink(missing_ok=True))

        script_content = Path(script_path).read_text()
        lines = script_content.split("\n")

        assert "deactivate.d" in script_content, (
            "Unix wrapper script should check for deactivation scripts"
        )

        echo_line_idx = None
        deactivate_check_idx = None
        for idx, line in enumerate(lines):
            if "echo" in line and "test" in line:
                echo_line_idx = idx
            if "deactivate.d" in line and ("CONDA_PREFIX" in line or "-d" in line):
                deactivate_check_idx = idx

        assert deactivate_line_idx is not None, (
            "Could not find deactivate.d directory check in the wrapper script"
        )
        assert echo_line_idx is not None, (
            "Could not find the user's command in the wrapper script"
        )
        # Verify deactivation check comes after the user's command
        assert deactivate_line_idx > echo_line_idx, (
            "Deactivation check should come after the user's command"
        )
