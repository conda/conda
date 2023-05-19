# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import json
import os.path
import pathlib
import tempfile
from unittest import mock

import pytest
from pytest_mock import MockerFixture

from conda.base.context import context, locate_prefix_by_name
from conda.exceptions import CondaError, EnvironmentNameNotFound
from conda.testing.helpers import run_inprocess_conda_command as run

TEST_ENV_NAME_1 = "env-1"
TEST_ENV_NAME_2 = "env-2"
TEST_ENV_NAME_RENAME = "renamed-env"

ENV_LIST_COMMAND = "conda env list --json"


@pytest.fixture(scope="module")
def env_one():
    """
    This fixture has been given a module scope to help decrease execution time.
    When using the fixture, please rename the original environment back to what it
    was (i.e. always make sure there is a TEST_ENV_NAME_1 present).
    """
    # Setup
    run(f"conda create -n {TEST_ENV_NAME_1} -y", disallow_stderr=False)

    yield

    # Teardown
    run(f"conda remove --all -y -n {TEST_ENV_NAME_1}", disallow_stderr=False)
    run(f"conda remove --all -y -n {TEST_ENV_NAME_RENAME}", disallow_stderr=False)


@pytest.fixture
def env_two():
    # Setup
    run(f"conda create -n {TEST_ENV_NAME_2} -y", disallow_stderr=False)

    yield

    # Teardown
    run(f"conda remove --all -y -n {TEST_ENV_NAME_2}", disallow_stderr=False)


@pytest.fixture
def env_prefix_one():
    """Used to get an environment created using -p flag"""
    # Setup
    tmpdir = tempfile.mkdtemp()
    run(f"conda create -p {tmpdir} -y", disallow_stderr=False)

    yield tmpdir

    # Teardown
    run(f"conda remove --all -y -p {tmpdir}", disallow_stderr=False)


def list_envs():
    out, err, exit_code = run(ENV_LIST_COMMAND)
    data = json.loads(out)

    return (out, err, exit_code), data


def test_rename_by_name_success(env_one):
    run(
        f"conda rename -n {TEST_ENV_NAME_1} {TEST_ENV_NAME_RENAME}",
        disallow_stderr=False,
    )

    assert locate_prefix_by_name(TEST_ENV_NAME_RENAME)
    with pytest.raises(EnvironmentNameNotFound):
        locate_prefix_by_name(TEST_ENV_NAME_1)

    # Clean up
    run(
        f"conda rename -n {TEST_ENV_NAME_RENAME} {TEST_ENV_NAME_1}",
        disallow_stderr=False,
    )


def test_rename_by_path_success(env_one):
    with tempfile.TemporaryDirectory() as temp_dir:
        new_name = str(pathlib.Path(temp_dir).joinpath("new-env"))
        run(f"conda rename -n {TEST_ENV_NAME_1} {new_name}", disallow_stderr=False)

        (out, err, exit_code), data = list_envs()
        result = data.get("envs", [])

        # Clean up
        run(f"conda rename -p {new_name} {TEST_ENV_NAME_1}")

        path_appears_in_env_list = any(new_name == path for path in result)
        original_name_in_envs = any(path.endswith(TEST_ENV_NAME_1) for path in result)

        assert path_appears_in_env_list
        assert not original_name_in_envs
        assert exit_code is None


def test_rename_by_name_name_already_exists_error(env_one):
    """Test to ensure that we do not rename if the name already exists"""
    out, err, exit_code = run(
        f"conda rename -n {TEST_ENV_NAME_1} {TEST_ENV_NAME_1}", disallow_stderr=False
    )
    assert (
        f"The environment '{TEST_ENV_NAME_1}' already exists. Override with --force"
        in err
    )


def test_rename_by_path_path_already_exists_error(env_one):
    """Test to ensure that we do not rename if the path already exists"""
    with tempfile.TemporaryDirectory() as tempdir:
        out, err, exit_code = run(
            f"conda rename -n {TEST_ENV_NAME_1} {tempdir}", disallow_stderr=False
        )
        assert (
            f"The environment '{os.path.basename(os.path.normpath(tempdir))}' already exists. Override with --force"
            in err
        )


def test_cannot_rename_base_env_by_name(env_one):
    """Test to ensure that we cannot rename the base env invoked by name"""
    out, err, exit_code = run(
        f"conda rename -n base {TEST_ENV_NAME_RENAME}", disallow_stderr=False
    )
    assert "The 'base' environment cannot be renamed" in err


def test_cannot_rename_base_env_by_path(env_one):
    """Test to ensure that we cannot rename the base env invoked by path"""
    out, err, exit_code = run(
        f"conda rename -p {context.root_prefix} {TEST_ENV_NAME_RENAME}",
        disallow_stderr=False,
    )
    assert "The 'base' environment cannot be renamed" in err


def test_cannot_rename_active_env_by_name(env_one, mocker: MockerFixture):
    """Makes sure that we cannot rename our active environment."""
    _, data = list_envs()
    result = data.get("envs", [])

    prefix_list = [res for res in result if res.endswith(TEST_ENV_NAME_1)]

    assert len(prefix_list) > 0

    mocker.patch(
        "conda.base.context.Context.active_prefix",
        new_callable=mocker.PropertyMock,
        return_value=prefix_list[0],
    )

    out, err, exit_code = run(
        f"conda rename -n {TEST_ENV_NAME_1} {TEST_ENV_NAME_RENAME}",
        disallow_stderr=False,
    )
    assert "Cannot rename the active environment" in err


def test_rename_with_force(env_one, env_two):
    """
    Runs a test where we specify the --force flag to remove an existing directory.
    Without this flag, it would return with an error message.
    """
    # Do a force rename
    run(
        f"conda rename -n {TEST_ENV_NAME_1} {TEST_ENV_NAME_2} --force",
        disallow_stderr=False,
    )

    (_, _, exit_code), _ = list_envs()

    assert locate_prefix_by_name(TEST_ENV_NAME_2)
    with pytest.raises(EnvironmentNameNotFound):
        locate_prefix_by_name(TEST_ENV_NAME_1)
    assert exit_code is None

    # Clean up
    run(f"conda rename -n {TEST_ENV_NAME_2} {TEST_ENV_NAME_1}", disallow_stderr=False)


def test_rename_with_force_with_errors(env_one, env_two):
    """
    Runs a test where we specify the --force flag to remove an existing directory.
    Additionally, in this test, we mock an exception to recreate a failure condition.
    """
    error_message = "Error Message"

    # Do a force rename
    with mock.patch("conda.cli.main_rename.install.clone") as clone_mock:
        clone_mock.side_effect = [CondaError(error_message)]
        _, err, exit_code = run(
            f"conda rename -n {TEST_ENV_NAME_1} {TEST_ENV_NAME_2} --force",
            disallow_stderr=False,
        )
        assert error_message in err
        assert exit_code == 1

    # Make sure both environments still exist
    assert locate_prefix_by_name(TEST_ENV_NAME_2)
    assert locate_prefix_by_name(TEST_ENV_NAME_1)
    (_, _, exit_code), _ = list_envs()
    assert exit_code is None


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
        out, err, exit_code = run(
            f"conda rename -p {env_prefix_one} {tmpdir} --force", disallow_stderr=False
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
    (rename_out, rename_err, rename_exit_code) = run(
        f"conda rename -n {TEST_ENV_NAME_1} {TEST_ENV_NAME_RENAME} --dry-run",
        disallow_stderr=False,
    )

    (out, err, exit_code), data = list_envs()
    data.get("envs", [])

    assert locate_prefix_by_name(TEST_ENV_NAME_1)
    with pytest.raises(EnvironmentNameNotFound):
        locate_prefix_by_name(TEST_ENV_NAME_RENAME)
    assert exit_code is None

    rename_stdout = str(rename_out)
    assert "Dry run action: clone" in rename_stdout
    assert "Dry run action: rm_rf" in rename_stdout
    assert exit_code is None


def test_rename_with_force_and_dry_run(env_one, env_prefix_one):
    """
    Runs a test where we specify the --force and --dry-run flags to forcefully rename
    an existing directory. We need to ensure that --dry-run is effective and that no
    changes occur.
    """
    (rename_out, rename_err, rename_exit_code) = run(
        f"conda rename -n {TEST_ENV_NAME_1} {TEST_ENV_NAME_RENAME} --force --dry-run",
        disallow_stderr=False,
    )

    (out, err, exit_code), data = list_envs()
    data.get("envs", [])

    assert locate_prefix_by_name(TEST_ENV_NAME_1)
    with pytest.raises(EnvironmentNameNotFound):
        locate_prefix_by_name(TEST_ENV_NAME_RENAME)
    assert exit_code is None

    rename_stdout = str(rename_out)
    assert (
        f"Dry run action: rename_context {os.path.join(context.envs_dirs[0], TEST_ENV_NAME_RENAME)} >"
        in rename_stdout
    )
    assert "Dry run action: clone" in rename_stdout
    assert "Dry run action: rm_rf" in rename_stdout
    assert rename_exit_code is None
