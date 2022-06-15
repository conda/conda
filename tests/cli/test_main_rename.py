# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import json
import pathlib
import subprocess
import tempfile

import pytest

from conda.base.context import context

TEST_ENV_NAME_1 = "env-1"
TEST_ENV_NAME_2 = "env-2"
TEST_ENV_NAME_RENAME = "renamed-env"

ENV_LIST_COMMAND = ["conda", "env", "list", "--json"]


@pytest.fixture(scope="module")
def env_one():
    """
    This fixture has been given a module scope to help decrease execution time.
    When using the fixture, please rename the original environment back to what it
    was (i.e. always make sure there is a TEST_ENV_NAME_1 present).
    """
    subprocess.run(["conda", "create", "-n", TEST_ENV_NAME_1], check=True)
    yield
    subprocess.run(["conda", "env", "remove", "-n", TEST_ENV_NAME_1], check=True)
    subprocess.run(["conda", "env", "remove", "-n", TEST_ENV_NAME_RENAME], check=True)


@pytest.fixture
def env_two():
    subprocess.run(["conda", "create", "-n", TEST_ENV_NAME_2], check=True)
    yield
    subprocess.run(["conda", "env", "remove", "-n", TEST_ENV_NAME_2], check=True)


def list_envs() -> tuple[subprocess.CompletedProcess, dict]:
    proc_res = subprocess.run(ENV_LIST_COMMAND, check=True, capture_output=True)
    data = json.loads(proc_res.stdout)

    return proc_res, data


@pytest.mark.integration
def test_rename_by_name_success(env_one):
    subprocess.run(["conda", "rename", "-n", TEST_ENV_NAME_1, TEST_ENV_NAME_RENAME], check=True)

    proc_res, data = list_envs()
    result = data.get("envs", [])

    # Clean up
    subprocess.run(["conda", "rename", "-n", TEST_ENV_NAME_RENAME, TEST_ENV_NAME_1], check=True)

    rename_appears_in_envs = any(path.endswith(TEST_ENV_NAME_RENAME) for path in result)
    original_name_in_envs = any(path.endswith(TEST_ENV_NAME_1) for path in result)

    assert rename_appears_in_envs
    assert not original_name_in_envs
    assert proc_res.stderr == b""


@pytest.mark.integration
def test_rename_by_path_success(env_one):
    with tempfile.TemporaryDirectory() as temp_dir:
        new_name = str(pathlib.Path(temp_dir).joinpath("new-env"))
        subprocess.run(["conda", "rename", "-p", TEST_ENV_NAME_1, new_name], check=True)

        proc_res, data = list_envs()
        result = data.get("envs", [])

        # Clean up
        subprocess.run(["conda", "rename", "-p", new_name, TEST_ENV_NAME_1], check=True)

        path_appears_in_env_list = any(new_name == path for path in result)
        original_name_in_envs = any(path.endswith(TEST_ENV_NAME_1) for path in result)

        assert path_appears_in_env_list
        assert not original_name_in_envs
        assert proc_res.stderr == b""


@pytest.mark.integration
def test_rename_by_name_name_already_exists_error(env_one):
    """Test to ensure that we do not rename if the name already exists"""
    proc_res = subprocess.run(
        ["conda", "rename", "-p", TEST_ENV_NAME_1, TEST_ENV_NAME_1], capture_output=True
    )
    assert "Environment destination already exists" in str(proc_res.stderr)


@pytest.mark.integration
def test_rename_by_path_path_already_exists_error(env_one):
    """Test to ensure that we do not rename if the path already exists"""
    with tempfile.TemporaryDirectory() as tempdir:
        proc_res = subprocess.run(
            ["conda", "rename", "-p", TEST_ENV_NAME_1, tempdir], capture_output=True
        )
        assert "Environment destination already exists" in str(proc_res.stderr)


@pytest.mark.integration
def test_rename_base_env_by_name_error(env_one):
    """Test to ensure that we cannot rename the base env invoked by name"""
    proc_res = subprocess.run(
        ["conda", "rename", "-n", "base", TEST_ENV_NAME_RENAME], capture_output=True
    )
    assert "The 'base' environment cannot be renamed" in str(proc_res.stderr)


@pytest.mark.integration
def test_rename_base_env_by_path_error(env_one):
    """Test to ensure that we cannot rename the base env invoked by path"""
    proc_res = subprocess.run(
        ["conda", "rename", "-p", context.root_prefix, TEST_ENV_NAME_RENAME], capture_output=True
    )
    assert "The 'base' environment cannot be renamed" in str(proc_res.stderr)


@pytest.mark.integration
def test_rename_with_force(env_one, env_two):
    """
    Runs a test where we specify the --force flag to remove an existing directory.
    Without this flag, it would return with an error message.
    """
    # Do a force rename
    subprocess.run(
        ["conda", "rename", "-n", TEST_ENV_NAME_1, TEST_ENV_NAME_2, "--force"], check=True
    )

    proc_res, data = list_envs()
    result = data.get("envs", [])

    # Clean up
    subprocess.run(["conda", "rename", "-n", TEST_ENV_NAME_2, TEST_ENV_NAME_1], check=True)

    rename_appears_in_envs = any(path.endswith(TEST_ENV_NAME_2) for path in result)
    force_name_not_in_envs = not any(path.endswith(TEST_ENV_NAME_1) for path in result)

    assert rename_appears_in_envs
    assert force_name_not_in_envs
    assert proc_res.stderr == b""


@pytest.mark.integration
def test_rename_with_dry_run(env_one):
    """
    Runs a test where we specify the --dry-run flag to remove an existing directory.
    Without this flag, it would actually execute all the actions.
    """
    rename_res = subprocess.run(
        ["conda", "rename", "-n", TEST_ENV_NAME_1, TEST_ENV_NAME_RENAME, "--dry-run"],
        check=True,
        capture_output=True,
    )

    proc_res, data = list_envs()
    result = data.get("envs", [])

    rename_appears_in_envs = any(path.endswith(TEST_ENV_NAME_1) for path in result)
    force_name_not_in_envs = not any(path.endswith(TEST_ENV_NAME_RENAME) for path in result)

    assert rename_appears_in_envs
    assert force_name_not_in_envs
    assert proc_res.stderr == b""

    rename_stdout = str(rename_res.stdout)
    assert "Dry run action: clone" in rename_stdout
    assert "Dry run action: rm_rf" in rename_stdout
    assert rename_res.stderr == b""
