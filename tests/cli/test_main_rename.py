# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import json
import os.path
import pathlib
import tempfile
import uuid
from typing import Iterable

import pytest
from pytest_mock import MockerFixture

from conda.base.context import context, locate_prefix_by_name
from conda.core.envs_manager import list_all_known_prefixes
from conda.exceptions import CondaError, EnvironmentNameNotFound
from conda.testing.helpers import set_active_prefix


@pytest.fixture
def env_rename() -> Iterable[str]:
    # Setup
    name = uuid.uuid4().hex

    yield name

    # Teardown
    conda_cli("remove", "--all", "-y", "-n", name)


@pytest.fixture
def env_one() -> Iterable[str]:
    # Setup
    name = uuid.uuid4().hex
    conda_cli("create", "-n", name, "-y")

    yield name

    # Teardown
    conda_cli("remove", "--all", "-y", "-n", name)


@pytest.fixture
def env_two() -> Iterable[str]:
    # Setup
    name = uuid.uuid4().hex
    conda_cli("create", "-n", name, "-y")

    yield name

    # Teardown
    conda_cli("remove", "--all", "-y", "-n", name)


@pytest.fixture
def env_prefix_one() -> Iterable[Path]:
    """Used to get an environment created using -p flag"""
    # Setup
    tmpdir = tempfile.mkdtemp()
    conda_cli("create", "-p", tmpdir, "-y")

    yield tmpdir

    # Teardown
    conda_cli("remove", "--all", "-y", "-p", tmpdir)


def test_rename_by_name_success(env_one: str, env_rename: str):
    conda_cli("rename", "-n", env_one, env_rename)

    assert locate_prefix_by_name(env_rename)
    with pytest.raises(EnvironmentNameNotFound):
        locate_prefix_by_name(env_one)


def test_rename_by_path_success(env_one: str):
    with tempfile.TemporaryDirectory() as temp_dir:
        new_name = str(pathlib.Path(temp_dir).joinpath("new-env"))
        conda_cli("rename", "-n", env_one, new_name)

        result = list_all_known_prefixes()

        path_appears_in_env_list = any(new_name == path for path in result)
        original_name_in_envs = any(path.endswith(env_one) for path in result)

        assert path_appears_in_env_list
        assert not original_name_in_envs


def test_rename_by_name_name_already_exists_error(env_one: str):
    """Test to ensure that we do not rename if the name already exists"""
    out, err, exit_code = conda_cli("rename", "-n", env_one, env_one)
    assert f"The environment '{env_one}' already exists. Override with --force" in err


def test_rename_by_path_path_already_exists_error(env_one: str):
    """Test to ensure that we do not rename if the path already exists"""
    with tempfile.TemporaryDirectory() as tempdir:
        out, err, exit_code = conda_cli("rename", "-n", env_one, tempdir)
        assert (
            f"The environment '{os.path.basename(os.path.normpath(tempdir))}' already exists. Override with --force"
            in err
        )


def test_cannot_rename_base_env_by_name(env_rename: str):
    """Test to ensure that we cannot rename the base env invoked by name"""
    out, err, exit_code = conda_cli("rename", "-n", "base", env_rename)
    assert "The 'base' environment cannot be renamed" in err


def test_cannot_rename_base_env_by_path(env_rename: str):
    """Test to ensure that we cannot rename the base env invoked by path"""
    out, err, exit_code = conda_cli("rename", "-p", context.root_prefix, env_rename)
    assert "The 'base' environment cannot be renamed" in err


def test_cannot_rename_active_env_by_name(env_one: str, env_rename: str):
    """Makes sure that we cannot rename our active environment."""
    result = list_all_known_prefixes()

    prefix_list = [res for res in result if res.endswith(env_one)]

    assert len(prefix_list) > 0

    prefix = prefix_list[0]

    with set_active_prefix(prefix):
        out, err, exit_code = conda_cli("rename", "-n", env_one, env_rename)
        assert "Cannot rename the active environment" in err


def test_rename_with_force(env_one: str, env_two: str):
    """
    Runs a test where we specify the --force flag to remove an existing directory.
    Without this flag, it would return with an error message.
    """
    # Do a force rename
    conda_cli("rename", "-n", env_one, env_two, "--force")

    assert locate_prefix_by_name(env_two)
    with pytest.raises(EnvironmentNameNotFound):
        locate_prefix_by_name(env_one)


def test_rename_with_force_with_errors(
    env_one: str, env_two: str, mocker: MockerFixture
):
    """
    Runs a test where we specify the --force flag to remove an existing directory.
    Additionally, in this test, we mock an exception to recreate a failure condition.
    """
    error_message = uuid.uuid4().hex
    mocker.patch(
        "conda.cli.main_rename.install.clone", side_effect=CondaError(error_message)
    )
    with pytest.raises(CondaError, match=error_message):
        conda_cli("rename", "-n", env_one, env_two, "--force")

    # Make sure both environments still exist
    assert locate_prefix_by_name(env_two)
    assert locate_prefix_by_name(env_one)


def test_rename_with_force_with_errors_prefix(
    env_prefix_one, mocker: MockerFixture, tmp_path: Path
):
    """
    Runs a test using --force flag while mocking an exception.
    Specifically targets environments created using the -p flag.
    """
    error_message = uuid.uuid4().hex
    mocker.patch(
        "conda.cli.main_rename.install.clone", side_effect=CondaError(error_message)
    )
    with pytest.raises(CondaError, match=error_message):
        conda_cli("rename", "-p", env_prefix_one, tmpdir, "--force")

    # Make sure both directories still exist
    assert os.path.isdir(tmpdir)
    assert os.path.isdir(env_prefix_one)


def test_rename_with_dry_run(env_one: str, env_rename: str):
    """
    Runs a test where we specify the --dry-run flag to remove an existing directory.
    Without this flag, it would actually execute all the actions.
    """
    (rename_out, rename_err, rename_exit_code) = conda_cli(
        "rename", "-n", env_one, env_rename, "--dry-run"
    )

    assert locate_prefix_by_name(env_one)
    with pytest.raises(EnvironmentNameNotFound):
        locate_prefix_by_name(env_rename)

    rename_stdout = str(rename_out)
    assert "Dry run action: clone" in rename_stdout
    assert "Dry run action: rm_rf" in rename_stdout


def test_rename_with_force_and_dry_run(env_one: str, env_prefix_one, env_rename: str):
    """
    Runs a test where we specify the --force and --dry-run flags to forcefully rename
    an existing directory. We need to ensure that --dry-run is effective and that no
    changes occur.
    """
    (rename_out, rename_err, rename_exit_code) = conda_cli(
        "rename", "-n", env_one, env_rename, "--force", "--dry-run"
    )

    assert locate_prefix_by_name(env_one)
    with pytest.raises(EnvironmentNameNotFound):
        locate_prefix_by_name(env_rename)

    rename_stdout = str(rename_out)
    assert (
        f"Dry run action: rename_context {os.path.join(context.envs_dirs[0], env_rename)} >"
        in rename_stdout
    )
    assert "Dry run action: clone" in rename_stdout
    assert "Dry run action: rm_rf" in rename_stdout
    assert rename_exit_code is None
