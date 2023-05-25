# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Iterable

import pytest
from pytest_mock import MockerFixture

from conda.base.context import context, locate_prefix_by_name
from conda.core.envs_manager import list_all_known_prefixes
from conda.exceptions import CondaEnvException, CondaError, EnvironmentNameNotFound
from conda.testing import CondaCLIFixture, PathFactoryFixture, TmpEnvFixture
from conda.testing.helpers import set_active_prefix


@pytest.fixture
def env_rename(conda_cli: CondaCLIFixture) -> Iterable[str]:
    # Setup
    name = uuid.uuid4().hex

    yield name

    # Teardown
    conda_cli("remove", "--all", "--yes", "--name", name)


@pytest.fixture
def env_one(conda_cli: CondaCLIFixture) -> Iterable[str]:
    # Setup
    name = uuid.uuid4().hex
    conda_cli("create", "--name", name, "--yes")

    yield name

    # Teardown
    conda_cli("remove", "--all", "--yes", "--name", name)


@pytest.fixture
def env_two(conda_cli: CondaCLIFixture) -> Iterable[str]:
    # Setup
    name = uuid.uuid4().hex
    conda_cli("create", "--name", name, "--yes")

    yield name

    # Teardown
    conda_cli("remove", "--all", "--yes", "--name", name)


def test_rename_by_name_success(
    conda_cli: CondaCLIFixture, env_one: str, env_rename: str
):
    conda_cli("rename", "--name", env_one, env_rename)

    assert locate_prefix_by_name(env_rename)
    with pytest.raises(EnvironmentNameNotFound):
        locate_prefix_by_name(env_one)


def test_rename_by_path_success(
    conda_cli: CondaCLIFixture, env_one: str, path_factory: PathFactoryFixture
):
    prefix = path_factory()
    conda_cli("rename", "--name", env_one, prefix)

    assert any(map(prefix.samefile, list_all_known_prefixes()))
    with pytest.raises(EnvironmentNameNotFound):
        locate_prefix_by_name(env_one)


def test_rename_by_name_name_already_exists_error(
    conda_cli: CondaCLIFixture, env_one: str
):
    """Test to ensure that we do not rename if the name already exists"""
    with pytest.raises(
        CondaEnvException,
        match=f"The environment '{env_one}' already exists. Override with --force",
    ):
        conda_cli("rename", "--name", env_one, env_one)


def test_rename_by_path_path_already_exists_error(
    conda_cli: CondaCLIFixture, env_one: str, tmp_path: Path
):
    """Test to ensure that we do not rename if the path already exists"""
    with pytest.raises(
        CondaEnvException,
        match=f"The environment '{tmp_path.name}' already exists. Override with --force",
    ):
        conda_cli("rename", "--name", env_one, tmp_path)


def test_cannot_rename_base_env_by_name(conda_cli: CondaCLIFixture, env_rename: str):
    """Test to ensure that we cannot rename the base env invoked by name"""
    with pytest.raises(
        CondaEnvException, match="The 'base' environment cannot be renamed"
    ):
        conda_cli("rename", "--name", "base", env_rename)


def test_cannot_rename_base_env_by_path(conda_cli: CondaCLIFixture, env_rename: str):
    """Test to ensure that we cannot rename the base env invoked by path"""
    with pytest.raises(
        CondaEnvException, match="The 'base' environment cannot be renamed"
    ):
        conda_cli("rename", "--prefix", context.root_prefix, env_rename)


def test_cannot_rename_active_env_by_name(
    conda_cli: CondaCLIFixture, env_one: str, env_rename: str
):
    """Makes sure that we cannot rename our active environment."""
    result = list_all_known_prefixes()

    prefix_list = [res for res in result if res.endswith(env_one)]

    assert len(prefix_list) > 0

    prefix = prefix_list[0]

    with set_active_prefix(prefix), pytest.raises(
        CondaEnvException, match="Cannot rename the active environment"
    ):
        conda_cli("rename", "--name", env_one, env_rename)


def test_rename_with_force(conda_cli: CondaCLIFixture, env_one: str, env_two: str):
    """
    Runs a test where we specify the --force flag to remove an existing directory.
    Without this flag, it would return with an error message.
    """
    # Do a force rename
    conda_cli("rename", "--name", env_one, env_two, "--force")

    assert locate_prefix_by_name(env_two)
    with pytest.raises(EnvironmentNameNotFound):
        locate_prefix_by_name(env_one)


def test_rename_with_force_with_errors(
    conda_cli: CondaCLIFixture, env_one: str, env_two: str, mocker: MockerFixture
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
        conda_cli("rename", "--name", env_one, env_two, "--force")

    # Make sure both environments still exist
    assert locate_prefix_by_name(env_two)
    assert locate_prefix_by_name(env_one)


def test_rename_with_force_with_errors_prefix(
    conda_cli: CondaCLIFixture,
    mocker: MockerFixture,
    tmp_env: TmpEnvFixture,
    tmp_path: Path,
):
    """
    Runs a test using --force flag while mocking an exception.
    Specifically targets environments created using the -p flag.
    """
    error_message = uuid.uuid4().hex
    mocker.patch(
        "conda.cli.main_rename.install.clone", side_effect=CondaError(error_message)
    )
    with tmp_env() as prefix:
        with pytest.raises(CondaError, match=error_message):
            conda_cli("rename", "--prefix", prefix, tmp_path, "--force")

        # Make sure both directories still exist
        assert tmp_path.is_dir()
        assert prefix.is_dir()


def test_rename_with_dry_run(conda_cli: CondaCLIFixture, env_one: str, env_rename: str):
    """
    Runs a test where we specify the --dry-run flag to remove an existing directory.
    Without this flag, it would actually execute all the actions.
    """
    stdout, stderr, err = conda_cli(
        "rename", "--name", env_one, env_rename, "--dry-run"
    )

    assert locate_prefix_by_name(env_one)
    with pytest.raises(EnvironmentNameNotFound):
        locate_prefix_by_name(env_rename)

    assert "Dry run action: clone" in stdout
    assert "Dry run action: rm_rf" in stdout
    assert not stderr
    assert not err


def test_rename_with_force_and_dry_run(
    conda_cli: CondaCLIFixture, env_one: str, env_rename: str
):
    """
    Runs a test where we specify the --force and --dry-run flags to forcefully rename
    an existing directory. We need to ensure that --dry-run is effective and that no
    changes occur.
    """
    stdout, stderr, err = conda_cli(
        "rename", "--name", env_one, env_rename, "--force", "--dry-run"
    )

    assert locate_prefix_by_name(env_one)
    with pytest.raises(EnvironmentNameNotFound):
        locate_prefix_by_name(env_rename)

    assert (
        f"Dry run action: rename_context {Path(context.envs_dirs[0], env_rename)} >"
        in stdout
    )
    assert "Dry run action: clone" in stdout
    assert "Dry run action: rm_rf" in stdout
    assert not stderr
    assert not err
