# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import json
import pathlib
import tempfile

import pytest

from conda.base import context as ctx
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
    run(f"conda create -n {TEST_ENV_NAME_1} -y")
    yield
    run(f"conda env remove -n {TEST_ENV_NAME_1}", disallow_stderr=False)
    run(f"conda env remove -n {TEST_ENV_NAME_RENAME}", disallow_stderr=False)


@pytest.fixture
def env_two():
    run(f"conda create -n {TEST_ENV_NAME_2} -y")
    yield
    run(f"conda env remove -n {TEST_ENV_NAME_2}", disallow_stderr=False)


def list_envs():
    out, err, exit_code = run(ENV_LIST_COMMAND)
    data = json.loads(out)

    return (out, err, exit_code), data


def test_rename_by_name_success(env_one):
    run(f"conda rename -n {TEST_ENV_NAME_1} {TEST_ENV_NAME_RENAME}")

    (out, err, exit_code), data = list_envs()
    result = data.get("envs", [])

    # Clean up
    run(f"conda rename -n {TEST_ENV_NAME_RENAME} {TEST_ENV_NAME_1}")

    rename_appears_in_envs = any(path.endswith(TEST_ENV_NAME_RENAME) for path in result)
    original_name_in_envs = any(path.endswith(TEST_ENV_NAME_1) for path in result)

    assert rename_appears_in_envs
    assert not original_name_in_envs
    assert err == ""


def test_rename_by_path_success(env_one):
    with tempfile.TemporaryDirectory() as temp_dir:
        new_name = str(pathlib.Path(temp_dir).joinpath("new-env"))
        run(f"conda rename -n {TEST_ENV_NAME_1} {new_name}")

        (out, err, exit_code), data = list_envs()
        result = data.get("envs", [])

        # Clean up
        run(f"conda rename -p {new_name} {TEST_ENV_NAME_1}")

        path_appears_in_env_list = any(new_name == path for path in result)
        original_name_in_envs = any(path.endswith(TEST_ENV_NAME_1) for path in result)

        assert path_appears_in_env_list
        assert not original_name_in_envs
        assert err == ""


def test_rename_by_name_name_already_exists_error(env_one):
    """Test to ensure that we do not rename if the name already exists"""
    out, err, exit_code = run(
        f"conda rename -n {TEST_ENV_NAME_1} {TEST_ENV_NAME_1}", disallow_stderr=False
    )
    assert "Environment destination already exists" in err


def test_rename_by_path_path_already_exists_error(env_one):
    """Test to ensure that we do not rename if the path already exists"""
    with tempfile.TemporaryDirectory() as tempdir:
        out, err, exit_code = run(
            f"conda rename -n {TEST_ENV_NAME_1} {tempdir}", disallow_stderr=False
        )
        assert "Environment destination already exists" in err


def test_cannot_rename_base_env_by_name(env_one):
    """Test to ensure that we cannot rename the base env invoked by name"""
    out, err, exit_code = run(
        f"conda rename -n base {TEST_ENV_NAME_RENAME}", disallow_stderr=False
    )
    assert "The 'base' environment cannot be renamed" in err


def test_cannot_rename_base_env_by_path(env_one):
    """Test to ensure that we cannot rename the base env invoked by path"""
    out, err, exit_code = run(
        f"conda rename -p {ctx.context.root_prefix} {TEST_ENV_NAME_RENAME}", disallow_stderr=False
    )
    assert "The 'base' environment cannot be renamed" in err


def test_rename_with_force(env_one, env_two):
    """
    Runs a test where we specify the --force flag to remove an existing directory.
    Without this flag, it would return with an error message.
    """
    # Do a force rename
    run(f"conda rename -n {TEST_ENV_NAME_1} {TEST_ENV_NAME_2} --force")

    (out, err, exit_code), data = list_envs()
    result = data.get("envs", [])

    # Clean up
    run(f"conda rename -n {TEST_ENV_NAME_2} {TEST_ENV_NAME_1}")

    rename_appears_in_envs = any(path.endswith(TEST_ENV_NAME_2) for path in result)
    force_name_not_in_envs = not any(path.endswith(TEST_ENV_NAME_1) for path in result)

    assert rename_appears_in_envs
    assert force_name_not_in_envs
    assert err == ""


def test_rename_with_dry_run(env_one):
    """
    Runs a test where we specify the --dry-run flag to remove an existing directory.
    Without this flag, it would actually execute all the actions.
    """
    (rename_out, rename_err, rename_exit_code) = run(
        f"conda rename -n {TEST_ENV_NAME_1} {TEST_ENV_NAME_RENAME} --dry-run"
    )

    (out, err, exit_code), data = list_envs()
    result = data.get("envs", [])

    rename_appears_in_envs = any(path.endswith(TEST_ENV_NAME_1) for path in result)
    force_name_not_in_envs = not any(path.endswith(TEST_ENV_NAME_RENAME) for path in result)

    assert rename_appears_in_envs
    assert force_name_not_in_envs
    assert err == ""

    rename_stdout = str(rename_out)
    assert "Dry run action: clone" in rename_stdout
    assert "Dry run action: rm_rf" in rename_stdout
    assert rename_err == ""
