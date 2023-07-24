# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from conda.testing.helpers import run_inprocess_conda_command as run
from conda.testing.integration import make_temp_env


def test_conda_doctor_happy_path():
    """Make sure that we are able to call the ``conda doctor`` command"""

    out, err, code = run(f"conda doctor")

    assert not err  # no error message
    assert not code  # successful exit code


def test_conda_doctor_happy_path_verbose():
    """Make sure that we are able to run ``conda doctor`` command with the --verbose flag"""

    out, err, code = run(f"conda doctor --verbose")

    assert not err  # no error message
    assert not code  # successful exit code


def test_conda_doctor_happy_path_show_help():
    """Make sure that we are able to run ``conda doctor`` command with the --help flag"""

    out, err, code = run(f"conda doctor --help")

    assert "Display a health report for your environment." in out
    assert not err  # no error message
    assert not code  # successful exit code


def test_conda_doctor_with_test_environment():
    """Make sure that we are able to call ``conda doctor`` command for a specific environment"""

    with make_temp_env() as prefix:
        out, err, code = run(f"conda doctor --prefix '{prefix}'")

        assert "There are no packages with missing files." in out
        assert not err  # no error message
        assert not code  # successful exit code
