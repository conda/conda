# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import json
import os.path
import tempfile
import uuid
from pathlib import Path
from unittest import mock

import pytest

from conda.base.context import context, locate_prefix_by_name
from conda.core.envs_manager import list_all_known_prefixes
from conda.exceptions import CondaEnvException, CondaError, EnvironmentNameNotFound
from conda.testing.helpers import set_active_prefix
from conda.testing.integration import Commands, run_command


@pytest.fixture
def name_rename() -> Generator[str, None, None]:
    """A teardown fixture, removes the renamed environment if present."""
    name = uuid.uuid4().hex

    yield name

    run_command(Commands.REMOVE, name, "--all")


@pytest.fixture
def name_one(name_rename: str) -> Generator[str, None, None]:
    """A setup fixture, creates an empty testing environment and removes it at the end if present."""
    name = uuid.uuid4().hex
    run_command(Commands.CREATE, name)

    yield name

    run_command(Commands.REMOVE, name, "--all")


@pytest.fixture
def name_two() -> Generator[str, None, None]:
    """A setup fixture, creates an empty testing environment and removes it at the end if present."""
    name = uuid.uuid4().hex
    run_command(Commands.CREATE, name)

    yield name

    run_command(Commands.REMOVE, name, "--all")


@pytest.fixture
def prefix_rename() -> Generator[Path, None, None]:
    """A teardown fixture, removes the renamed environment if present."""
    with tempfile.TemporaryDirectory() as root:
        prefix = Path(root, uuid.uuid4().hex)

        yield prefix


@pytest.fixture
def prefix_one(prefix_rename: Path) -> Generator[Path, None, None]:
    """A setup fixture, creates an empty testing environment and removes it at the end if present."""
    with tempfile.TemporaryDirectory() as root:
        prefix = Path(root, uuid.uuid4().hex)
        run_command(Commands.CREATE, str(prefix))

        yield prefix


@pytest.fixture
def prefix_two() -> Generator[Path, None, None]:
    """A setup fixture, creates an empty testing environment and removes it at the end if present."""
    with tempfile.TemporaryDirectory() as root:
        prefix = Path(root, uuid.uuid4().hex)
        run_command(Commands.CREATE, str(prefix))

        yield prefix


def test_rename_by_name_success(name_one: str, name_rename: str):
    """Test renaming from one name to another unused name."""
    run_command(Commands.RENAME, name_one, name_rename)

    # only the new environment is present
    assert locate_prefix_by_name(name_rename)
    with pytest.raises(EnvironmentNameNotFound):
        locate_prefix_by_name(name_one)


def test_rename_by_path_success(name_one: str, prefix_rename: Path):
    """Test renaming from one name to another unused path."""
    run_command(Commands.RENAME, name_one, str(prefix_rename))

    # only the new environment is present
    assert any(prefix_rename.samefile(path) for path in list_all_known_prefixes())
    with pytest.raises(EnvironmentNameNotFound):
        locate_prefix_by_name(name_one)


def test_rename_by_name_name_already_exists_error(name_one: str):
    """Test to ensure that we do not rename if the name already exists"""
    with pytest.raises(CondaEnvException, match="already exists"):
        run_command(Commands.RENAME, name_one, name_one)


def test_rename_by_path_path_already_exists_error(name_one: str, prefix_one: Path):
    """Test to ensure that we do not rename if the path already exists"""
    with pytest.raises(CondaEnvException, match="already exists"):
        run_command(Commands.RENAME, name_one, str(prefix_one))


def test_cannot_rename_base_env_by_name(name_rename: str):
    """Test to ensure that we cannot rename the base env invoked by name"""
    with pytest.raises(CondaEnvException, match="cannot be renamed"):
        run_command(Commands.RENAME, "base", name_rename)


def test_cannot_rename_base_env_by_path(name_rename: str):
    """Test to ensure that we cannot rename the base env invoked by path"""
    with pytest.raises(CondaEnvException, match="cannot be renamed"):
        run_command(Commands.RENAME, context.root_prefix, name_rename)


def test_cannot_rename_active_env_by_name(name_one: str, name_rename: str):
    """
    Makes sure that we cannot rename our active environment.
    """
    prefix = locate_prefix_by_name(name_one)
    with set_active_prefix(prefix), pytest.raises(
        CondaEnvException, match="cannot be renamed"
    ):
        run_command(Commands.RENAME, name_one, name_rename)


def test_rename_with_force(name_one: str, name_two: str):
    """Test renaming to an existing name with --force."""
    run_command(Commands.RENAME, name_one, name_two, "--force")

    assert locate_prefix_by_name(name_two)
    with pytest.raises(EnvironmentNameNotFound):
        locate_prefix_by_name(name_one)


def test_rename_with_force_with_errors(
    mocker: MockerFixture,
    name_one: str,
    name_two: str,
):
    """
    Runs a test where we specify the --force flag to remove an existing directory.
    Additionally, in this test, we mock an exception to recreate a failure condition.
    """
    clone_mock = mocker.patch(
        "conda.cli.main_rename.install.clone",
        side_effect=CondaError("some error"),
    )

    with pytest.raises(CondaError, match="some error"):
        run_command(Commands.RENAME, name_one, name_two, "--force")

    # both environments still exist
    assert locate_prefix_by_name(name_one)
    assert locate_prefix_by_name(name_two)


def test_rename_with_force_with_errors_prefix(
    mocker: MockerFixture,
    prefix_one: Path,
    prefix_two: Path,
):
    """
    Runs a test using --force flag while mocking an exception.
    Specifically targets environments created using the -p flag.
    """
    clone_mock = mocker.patch(
        "conda.cli.main_rename.install.clone",
        side_effect=CondaError("some error"),
    )

    with pytest.raises(CondaError, match="some error"):
        run_command(Commands.RENAME, str(prefix_one), str(prefix_two), "--force")

    # both directories still exist
    assert prefix_one.is_dir()
    assert prefix_two.is_dir()


def test_rename_with_dry_run(name_one: str, name_rename: str):
    """
    Runs a test where we specify the --dry-run flag to remove an existing directory.
    Without this flag, it would actually execute all the actions.
    """
    out, _, _ = run_command(Commands.RENAME, name_one, name_rename, "--dry-run")

    # environments remain unchanged
    assert locate_prefix_by_name(name_one)
    with pytest.raises(EnvironmentNameNotFound):
        locate_prefix_by_name(name_rename)

    assert "Dry run action: clone" in out
    assert "Dry run action: rm_rf" in out


def test_rename_with_force_and_dry_run(name_one: str, name_rename: str):
    """
    Runs a test where we specify the --force and --dry-run flags to forcefully rename
    an existing directory. We need to ensure that --dry-run is effective and that no
    changes occur.
    """
    out, _, _ = run_command(
        Commands.RENAME, name_one, name_rename, "--force", "--dry-run"
    )

    # environments remain unchanged
    assert locate_prefix_by_name(name_one)
    with pytest.raises(EnvironmentNameNotFound):
        locate_prefix_by_name(name_rename)

    assert (
        f"Dry run action: rename_context {Path(context.envs_dirs[0], name_rename)} >"
        in out
    )
    assert "Dry run action: clone" in out
    assert "Dry run action: rm_rf" in out
