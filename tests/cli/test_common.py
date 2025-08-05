# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import os
from pathlib import Path

import pytest
from pytest import raises
from pytest_mock import MockerFixture

from conda.base.context import conda_tests_ctxt_mgmt_def_pol, context
from conda.cli.common import (
    check_non_admin,
    is_active_prefix,
    print_envs_list,
    validate_file_exists,
    validate_subdir_config,
)
from conda.common.compat import on_win
from conda.common.io import env_vars
from conda.exceptions import EnvironmentFileNotFound, OperationNotAllowed


def test_check_non_admin_enabled_false():
    with env_vars(
        {"CONDA_NON_ADMIN_ENABLED": "false"},
        stack_callback=conda_tests_ctxt_mgmt_def_pol,
    ):
        if on_win:
            from conda.common._os.windows import is_admin_on_windows

            if is_admin_on_windows():
                check_non_admin()
            else:
                with raises(OperationNotAllowed):
                    check_non_admin()
        else:
            if os.geteuid() == 0 or os.getegid() == 0:
                check_non_admin()
            else:
                with raises(OperationNotAllowed):
                    check_non_admin()


def test_check_non_admin_enabled_true():
    with env_vars(
        {"CONDA_NON_ADMIN_ENABLED": "true"},
        stack_callback=conda_tests_ctxt_mgmt_def_pol,
    ):
        check_non_admin()
        assert True


@pytest.mark.parametrize("prefix,active", [("", False), ("active_prefix", True)])
def test_is_active_prefix(prefix, active):
    if prefix == "active_prefix":
        prefix = context.active_prefix
    assert is_active_prefix(prefix) is active


def test_print_envs_list(capsys):
    """
    Test the case for print_envs_list when output=True

    TODO: this function is deprecated and this test should be remove when this function is removed
    """
    with pytest.deprecated_call():
        print_envs_list(["test"])

    capture = capsys.readouterr()

    assert "test" in capture.out


def test_print_envs_list_output_false(capsys):
    """
    Test the case for print_envs_list when output=False

    TODO: this function is deprecated and this test should be remove when this function is removed
    """

    with pytest.deprecated_call():
        print_envs_list(["test"], output=False)

    capture = capsys.readouterr()

    assert capture.out == ""


@pytest.mark.parametrize(
    "filename,exists",
    [
        (os.path.realpath(__file__), True),
        ("idontexist.txt", False),
        ("http://imasession.txt", True),
        ("file://idontexist.txt", False),
        (f"file://{os.path.realpath(__file__)}", True),
    ],
)
def test_validate_file_exists(filename, exists):
    """Test `validate_file_exists` can:
    - validate that a local file path exists
    - accept a URL scheme supported by CONDA_SESSION_SCHEMES
    - raise EnvironmentFileNotFound when the file does not exist or the url scheme is not supported
    """
    if exists:
        validate_file_exists(filename)
    else:
        with pytest.raises(EnvironmentFileNotFound):
            validate_file_exists(filename)


@pytest.fixture
def mock_subdir_context(mocker: MockerFixture):
    """Mock context with non-existent subdir and root prefix for subdir validation tests."""
    subdir = "idontexist"
    mocker.patch(
        "conda.base.context.Context.subdir",
        new_callable=mocker.PropertyMock,
        return_value=subdir,
    )

    mocker.patch(
        "conda.base.context.Context.root_prefix",
        new_callable=mocker.PropertyMock,
        return_value="/something/that/does/not/exist",
    )

    return subdir  # Return subdir value in case tests need it


def test_validate_subdir_config(mock_subdir_context, mocker: MockerFixture):
    """Test conda will validate the subdir config."""
    mocker.patch(
        "conda.base.context.Context.collect_all",
        return_value={
            "cmd_line": {"channels": ["conda-forge"]},
            Path("/path/to/a/condarc"): {"channels": ["defaults"]},
            Path("/path/to/another/condarc"): {"override_channels_enabled": "True"},
        },
    )

    validate_subdir_config()


def test_validate_subdir_config_invalid_subdir(
    mock_subdir_context, mocker: MockerFixture
):
    """Test conda will validate the subdir config. The configuration is
    invalid if it is coming from the active prefix"""
    subdir = mock_subdir_context  # Get the subdir value from fixture
    dummy_conda_rc = Path(context.active_prefix) / "condarc"

    mocker.patch(
        "conda.base.context.Context.collect_all",
        return_value={
            "cmd_line": {"channels": ["conda-forge"]},
            dummy_conda_rc: {"subdir": subdir},
            Path("/path/to/a/condarc"): {"channels": ["defaults"]},
        },
    )

    with pytest.raises(OperationNotAllowed):
        validate_subdir_config()
