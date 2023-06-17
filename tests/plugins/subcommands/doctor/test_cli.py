# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from argparse import Namespace
from pathlib import Path
from typing import Iterable

import pytest
from pytest import MonkeyPatch

from conda.base.context import conda_tests_ctxt_mgmt_def_pol, context
from conda.common.io import env_vars
from conda.exceptions import (
    CondaEnvException,
    DirectoryNotACondaEnvironmentError,
    EnvironmentNameNotFound,
)
from conda.plugins.subcommands.doctor.health_checks import MISSING_FILES_SUCCESS_MESSAGE
from conda.testing import TmpEnvFixture
from conda.testing.helpers import run_inprocess_conda_command as run


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


def test_conda_doctor_with_test_environment(tmp_env: TmpEnvFixture):
    """Make sure that we are able to call ``conda doctor`` command for a specific environment"""

    with tmp_env() as prefix:
        out, err, code = run(f"conda doctor --prefix '{prefix}'")

        assert MISSING_FILES_SUCCESS_MESSAGE in out
        assert not err  # no error message
        assert not code  # successful exit code
