# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import json
import os.path
import pathlib
import tempfile
from unittest import mock

import pytest

from conda.base.context import context, locate_prefix_by_name
from conda.core.envs_manager import list_all_known_prefixes
from conda.exceptions import CondaError, EnvironmentNameNotFound
from conda.testing.helpers import set_active_prefix

TEST_ENV_NAME_1 = "env-1"
TEST_ENV_NAME_2 = "env-2"
TEST_ENV_NAME_RENAME = "renamed-env"


@pytest.fixture(scope="module")
def env_one():
    """
    This fixture has been given a module scope to help decrease execution time.
    When using the fixture, please rename the original environment back to what it
    was (i.e. always make sure there is a TEST_ENV_NAME_1 present).
    """
    # Setup
    conda_cli("create", "-n", TEST_ENV_NAME_1, "-y")

    yield

    # Teardown
    conda_cli("remove", "--all", "-y", "-n", TEST_ENV_NAME_1)
    conda_cli("remove", "--all", "-y", "-n", TEST_ENV_NAME_RENAME)


@pytest.fixture
def env_two():
    # Setup
    conda_cli("create", "-n", TEST_ENV_NAME_2, "-y")

    yield

    # Teardown
    conda_cli("remove", "--all", "-y", "-n", TEST_ENV_NAME_2)


@pytest.fixture
def env_prefix_one():
    """Used to get an environment created using -p flag"""
    # Setup
    tmpdir = tempfile.mkdtemp()
    conda_cli("create", "-p", tmpdir, "-y")

    yield tmpdir

    # Teardown
    conda_cli("remove", "--all", "-y", "-p", tmpdir)


def test_rename_by_name_success(env_one):
    conda_cli("rename", "-n", TEST_ENV_NAME_1, TEST_ENV_NAME_RENAME)

    assert locate_prefix_by_name(TEST_ENV_NAME_RENAME)
    with pytest.raises(EnvironmentNameNotFound):
        locate_prefix_by_name(TEST_ENV_NAME_1)

    # Clean up
    conda_cli("rename", "-n", TEST_ENV_NAME_RENAME, TEST_ENV_NAME_1)


def test_rename_by_path_success(env_one):
    with tempfile.TemporaryDirectory() as temp_dir:
        new_name = str(pathlib.Path(temp_dir).joinpath("new-env"))
        conda_cli("rename", "-n", TEST_ENV_NAME_1, new_name)

        result = list_all_known_prefixes()

        # Clean up
        conda_cli("rename", "-p", new_name, TEST_ENV_NAME_1)

        path_appears_in_env_list = any(new_name == path for path in result)
        original_name_in_envs = any(path.endswith(TEST_ENV_NAME_1) for path in result)

        assert path_appears_in_env_list
        assert not original_name_in_envs


def test_rename_by_name_name_already_exists_error(env_one):
    """Test to ensure that we do not rename if the name already exists"""
    out, err, exit_code = conda_cli("rename", "-n", TEST_ENV_NAME_1, TEST_ENV_NAME_1)
    assert (
        f"The environment '{TEST_ENV_NAME_1}' already exists. Override with --force"
        in err
    )


def test_rename_by_path_path_already_exists_error(env_one):
    """Test to ensure that we do not rename if the path already exists"""
    with tempfile.TemporaryDirectory() as tempdir:
        out, err, exit_code = conda_cli("rename", "-n", TEST_ENV_NAME_1, tempdir)
        assert (
            f"The environment '{os.path.basename(os.path.normpath(tempdir))}' already exists. Override with --force"
            in err
        )


def test_cannot_rename_base_env_by_name(env_one):
    """Test to ensure that we cannot rename the base env invoked by name"""
    out, err, exit_code = conda_cli("rename", "-n", "base", TEST_ENV_NAME_RENAME)
    assert "The 'base' environment cannot be renamed" in err


def test_cannot_rename_base_env_by_path(env_one):
    """Test to ensure that we cannot rename the base env invoked by path"""
    out, err, exit_code = conda_cli(
        "rename", "-p", context.root_prefix, TEST_ENV_NAME_RENAME
    )
    assert "The 'base' environment cannot be renamed" in err


def test_cannot_rename_active_env_by_name(env_one):
    """Makes sure that we cannot rename our active environment."""
    result = list_all_known_prefixes()

    prefix_list = [res for res in result if res.endswith(TEST_ENV_NAME_1)]

    assert len(prefix_list) > 0

    prefix = prefix_list[0]

    with set_active_prefix(prefix):
        out, err, exit_code = conda_cli(
            "rename", "-n", TEST_ENV_NAME_1, TEST_ENV_NAME_RENAME
        )
        assert "Cannot rename the active environment" in err


def test_rename_with_force(env_one, env_two):
    """
    Runs a test where we specify the --force flag to remove an existing directory.
    Without this flag, it would return with an error message.
    """
    # Do a force rename
    conda_cli("rename", "-n", TEST_ENV_NAME_1, TEST_ENV_NAME_2, "--force")

    assert locate_prefix_by_name(TEST_ENV_NAME_2)
    with pytest.raises(EnvironmentNameNotFound):
        locate_prefix_by_name(TEST_ENV_NAME_1)

    # Clean up
    conda_cli("rename", "-n", TEST_ENV_NAME_2, TEST_ENV_NAME_1)


def test_rename_with_force_with_errors(env_one, env_two):
    """
    Runs a test where we specify the --force flag to remove an existing directory.
    Additionally, in this test, we mock an exception to recreate a failure condition.
    """
    error_message = "Error Message"

    # Do a force rename
    with mock.patch("conda.cli.main_rename.install.clone") as clone_mock:
        clone_mock.side_effect = [CondaError(error_message)]
        _, err, exit_code = conda_cli(
            "rename", "-n", TEST_ENV_NAME_1, TEST_ENV_NAME_2, "--force"
        )
        assert error_message in err
        assert exit_code == 1

    # Make sure both environments still exist
    assert locate_prefix_by_name(TEST_ENV_NAME_2)
    assert locate_prefix_by_name(TEST_ENV_NAME_1)


def test_rename_with_force_with_errors_prefix(env_prefix_one):
    """
    Runs a test using --force flag while mocking an exception.
    Specifically targets environments created using the -p flag.
    """
    error_message = "Error Message"

    # Do a force rename
    with mock.patch(
        "conda.cli.main_rename.install.clone"
    ) as clone_mock, tempfile.TemporaryDirectory() as tmpdir:
        clone_mock.side_effect = [CondaError(error_message)]
        out, err, exit_code = conda_cli(
            "rename", "-p", env_prefix_one, tmpdir, "--force"
        )
        assert error_message in err

        # Make sure both directories still exist
        assert os.path.isdir(tmpdir)
        assert os.path.isdir(env_prefix_one)


def test_rename_with_dry_run(env_one):
    """
    Runs a test where we specify the --dry-run flag to remove an existing directory.
    Without this flag, it would actually execute all the actions.
    """
    (rename_out, rename_err, rename_exit_code) = conda_cli(
        "rename", "-n", TEST_ENV_NAME_1, TEST_ENV_NAME_RENAME, "--dry-run"
    )

    assert locate_prefix_by_name(TEST_ENV_NAME_1)
    with pytest.raises(EnvironmentNameNotFound):
        locate_prefix_by_name(TEST_ENV_NAME_RENAME)

    rename_stdout = str(rename_out)
    assert "Dry run action: clone" in rename_stdout
    assert "Dry run action: rm_rf" in rename_stdout


def test_rename_with_force_and_dry_run(env_one, env_prefix_one):
    """
    Runs a test where we specify the --force and --dry-run flags to forcefully rename
    an existing directory. We need to ensure that --dry-run is effective and that no
    changes occur.
    """
    (rename_out, rename_err, rename_exit_code) = conda_cli(
        "rename", "-n", TEST_ENV_NAME_1, TEST_ENV_NAME_RENAME, "--force", "--dry-run"
    )

    assert locate_prefix_by_name(TEST_ENV_NAME_1)
    with pytest.raises(EnvironmentNameNotFound):
        locate_prefix_by_name(TEST_ENV_NAME_RENAME)

    rename_stdout = str(rename_out)
    assert (
        f"Dry run action: rename_context {os.path.join(context.envs_dirs[0], TEST_ENV_NAME_RENAME)} >"
        in rename_stdout
    )
    assert "Dry run action: clone" in rename_stdout
    assert "Dry run action: rm_rf" in rename_stdout
    assert rename_exit_code is None
