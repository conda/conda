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
