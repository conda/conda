# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import pytest

from conda.testing import CondaCLIFixture, TmpEnvFixture


def test_conda_doctor_happy_path(conda_cli: CondaCLIFixture):
    """Make sure that we are able to call the ``conda doctor`` command"""

    out, err, code = conda_cli(f"doctor")

    assert not err  # no error message
    assert not code  # successful exit code


def test_conda_doctor_happy_path_verbose(conda_cli: CondaCLIFixture):
    """Make sure that we are able to run ``conda doctor`` command with the --verbose flag"""

    out, err, code = conda_cli(f"doctor", "--verbose")

    assert not err  # no error message
    assert not code  # successful exit code


def test_conda_doctor_happy_path_show_help(conda_cli: CondaCLIFixture):
    """Make sure that we are able to run ``conda doctor`` command with the --help flag"""
    with pytest.raises(SystemExit):
        out, err, code = conda_cli("doctor", "--help")

        assert "Display a health report for your environment." in out
        assert not err  # no error message
        assert not code  # successful exit code


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
