# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from conda.exceptions import EnvironmentLocationNotFound

if TYPE_CHECKING:
    from conda.testing.fixtures import CondaCLIFixture, TmpEnvFixture


def test_conda_doctor_happy_path(conda_cli: CondaCLIFixture):
    """Make sure that we are able to call the ``conda doctor`` command"""

    out, err, code = conda_cli("doctor")

    assert not err  # no error message
    assert not code  # successful exit code


def test_conda_doctor_happy_path_verbose(conda_cli: CondaCLIFixture):
    """Make sure that we are able to run ``conda doctor`` command with the --verbose flag"""

    out, err, code = conda_cli("doctor", "--verbose")

    assert not err  # no error message
    assert not code  # successful exit code


def test_conda_doctor_happy_path_show_help(conda_cli: CondaCLIFixture):
    """Make sure that we are able to run ``conda doctor`` command with the --help flag"""
    with pytest.raises(SystemExit, match="0"):  # 0 is the return code ¯\_(ツ)_/¯
        conda_cli("doctor", "--help")


def test_conda_doctor_with_test_environment(
    conda_cli: CondaCLIFixture,
    tmp_env: TmpEnvFixture,
):
    """Make sure that we are able to call ``conda doctor`` command for a specific environment"""

    with tmp_env() as prefix:
        out, err, code = conda_cli("doctor", "--prefix", prefix)

        assert "There are no packages with missing files." in out
        assert not err  # no error message
        assert not code  # successful exit code


def test_conda_doctor_with_non_existent_environment(conda_cli: CondaCLIFixture):
    """Make sure that ``conda doctor`` detects a non existent environment path"""
    # with pytest.raises(EnvironmentLocationNotFound):
    out, err, exception = conda_cli(
        "doctor",
        "--prefix",
        Path("non/existent/path"),
        raises=EnvironmentLocationNotFound,
    )
    assert not out
    assert not err  # no error message
    assert exception


def test_conda_doctor_list(conda_cli: CondaCLIFixture):
    """Make sure --list shows available health checks."""
    out, err, code = conda_cli("doctor", "--list")

    assert "Available health checks:" in out
    assert "missing-files" in out  # built-in check
    assert not err
    assert not code


def test_conda_doctor_specific_check(
    conda_cli: CondaCLIFixture,
    tmp_env: TmpEnvFixture,
):
    """Make sure we can run a specific health check by id."""
    with tmp_env() as prefix:
        out, err, code = conda_cli("doctor", "missing-files", "--prefix", prefix)

        assert "There are no packages with missing files." in out
        # Should NOT run other checks like altered files
        assert (
            "altered" not in out.lower()
            or "no packages with altered files" in out.lower()
        )
        assert not err
        assert not code


def test_conda_doctor_fix_dry_run(
    conda_cli: CondaCLIFixture,
    tmp_env: TmpEnvFixture,
):
    """Make sure --fix --dry-run doesn't make actual changes."""
    with tmp_env() as prefix:
        out, err, code = conda_cli(
            "doctor",
            "--fix",
            "--dry-run",
            "--prefix",
            prefix,
        )
        # Dry run triggers DryRunExit which results in exit code 1
        # The important thing is that no actual changes are made
        assert "Running fixes" in out
        # Verify dry-run was triggered (logged as warning)
        assert "Dry run" in err


def test_conda_doctor_fix_yes(
    conda_cli: CondaCLIFixture,
    tmp_env: TmpEnvFixture,
):
    """Make sure --fix --yes skips confirmation prompts."""
    with tmp_env() as prefix:
        out, err, code = conda_cli(
            "doctor",
            "--fix",
            "--yes",
            "--prefix",
            prefix,
        )
        # Should complete without prompting
        assert not err
        assert not code
