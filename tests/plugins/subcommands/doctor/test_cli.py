# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import pytest

from conda.testing.helpers import run_inprocess_conda_command as run
from conda.plugins.subcommands.doctor.health_checks import MISSING_FILES_SUCCESS_MESSAGE


TEST_ENV_1 = "test-env-1"


def test_conda_doctor_happy_path():
    """Make sure that we are able to call the ``conda doctor`` command"""

    out, err, exit_code = run(f"conda doctor")

    assert err == ""  # no error message
    assert exit_code is None  # successful exit code


def test_conda_doctor_happy_path_verbose():
    """Make sure that we are able to run ``conda doctor`` command with the --verbose flag"""

    out, err, exit_code = run(f"conda doctor --verbose")

    assert err == ""  # no error message
    assert exit_code is None  # successful exit code


def test_conda_doctor_happy_path_show_help():
    """Make sure that we are able to run ``conda doctor`` command with the --help flag"""

    out, err, exit_code = run(f"conda doctor --help")

    assert "Display a health report for your environment." in out  # help text
    assert err == ""  # no error message
    assert exit_code == 0  # successful exit code


@pytest.fixture()
def env_one():
    """pytest fixture that creates and then deletes a new environemnt"""

    out, err, exit_code = run(f"conda create -n {TEST_ENV_1} -y")
    assert exit_code == 0

    yield

    out, err, exit_code = run(f"conda remove --all in {TEST_ENV_1}")

    assert exit_code == 0


@pytest.mark.skip("enable when conda doctor supports --name/--prefix")
def test_conda_doctor_with_test_environment(env_one):
    """Make sure that we are able to call ``conda doctor`` command for a specific environment"""

    out, err, exit_code = run(f"conda doctor --name {TEST_ENV_1}")

    assert MISSING_FILES_SUCCESS_MESSAGE in out
    assert err == ""  # no error message
    assert exit_code is None
