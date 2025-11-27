# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import os
from pathlib import Path

import pytest
from pytest import MonkeyPatch, raises
from pytest_mock import MockerFixture

from conda.base.context import context, reset_context
from conda.cli.common import (
    check_non_admin,
    is_active_prefix,
    print_activate,
    validate_file_exists,
    validate_subdir_config,
)
from conda.common.compat import on_win
from conda.exceptions import EnvironmentFileNotFound, OperationNotAllowed


def test_check_non_admin_enabled_false(monkeypatch: MonkeyPatch):
    monkeypatch.setenv("CONDA_NON_ADMIN_ENABLED", "false")
    reset_context()

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


def test_check_non_admin_enabled_true(monkeypatch: MonkeyPatch):
    monkeypatch.setenv("CONDA_NON_ADMIN_ENABLED", "true")
    reset_context()

    check_non_admin()
    assert True


@pytest.mark.parametrize("prefix,active", [("", False), ("active_prefix", True)])
def test_is_active_prefix(prefix, active):
    if prefix == "active_prefix":
        prefix = context.active_prefix
    assert is_active_prefix(prefix) is active


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


def test_print_activate(capsys):
    print_activate("test_env")

    captured = capsys.readouterr()

    assert "To activate this environment" in captured.out
    assert "To deactivate an active environment" in captured.out


@pytest.mark.parametrize("env_var", ["CONDA_QUIET", "CONDA_JSON"])
def test_print_activate_no_output(capsys, monkeypatch, env_var):
    monkeypatch.setenv(env_var, "true")
    reset_context()

    print_activate("test_env")

    captured = capsys.readouterr()
    assert captured.out == ""
