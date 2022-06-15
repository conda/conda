# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import json
import pathlib
import tempfile
from typing import Callable

import pytest

from conda.base.context import context
from conda.exceptions import CondaEnvException
from conda.testing.fixtures import conda_cli, conda_env_cli

TEST_ENV_NAME_1 = "env-1"
TEST_ENV_NAME_2 = "env-2"
TEST_ENV_NAME_RENAME = "renamed-env"

ENV_LIST_COMMAND = ["list", "--json"]


@pytest.fixture
def env_one(conda_cli, conda_env_cli):
    """
    This fixture has been given a module scope to help decrease execution time.
    When using the fixture, please rename the original environment back to what it
    was (i.e. always make sure there is a TEST_ENV_NAME_1 present).
    """
    conda_cli(["create", "-n", TEST_ENV_NAME_1, "-y"])
    yield
    conda_env_cli(["remove", "-n", TEST_ENV_NAME_1])
    conda_env_cli(["remove", "-n", TEST_ENV_NAME_RENAME])


@pytest.fixture
def env_two(conda_cli, conda_env_cli):
    conda_cli(["create", "-n", TEST_ENV_NAME_2, "-y"])
    yield
    conda_env_cli(["remove", "-n", TEST_ENV_NAME_2])


def list_envs(conda_env_cli: Callable):
    res = conda_env_cli(ENV_LIST_COMMAND)
    data = json.loads(res.out)

    return res, data


def test_rename_by_name_success(env_one, conda_cli, conda_env_cli):
    conda_cli(["rename", "-n", TEST_ENV_NAME_1, TEST_ENV_NAME_RENAME])

    res, data = list_envs(conda_env_cli)
    result = data.get("envs", [])

    # Clean up
    conda_cli(["rename", "-n", TEST_ENV_NAME_RENAME, TEST_ENV_NAME_1])

    rename_appears_in_envs = any(path.endswith(TEST_ENV_NAME_RENAME) for path in result)
    original_name_in_envs = any(path.endswith(TEST_ENV_NAME_1) for path in result)

    assert rename_appears_in_envs
    assert not original_name_in_envs
    assert res.err == ""


def test_rename_by_path_success(env_one, conda_cli, conda_env_cli):
    with tempfile.TemporaryDirectory() as temp_dir:
        new_name = str(pathlib.Path(temp_dir).joinpath("new-env"))
        conda_cli(["rename", "-p", TEST_ENV_NAME_1, new_name])

        res, data = list_envs(conda_env_cli)
        result = data.get("envs", [])

        # Clean up
        conda_cli(["rename", "-p", new_name, TEST_ENV_NAME_1])

        path_appears_in_env_list = any(new_name == path for path in result)
        original_name_in_envs = any(path.endswith(TEST_ENV_NAME_1) for path in result)

        assert path_appears_in_env_list
        assert not original_name_in_envs
        assert res.err == ""


def test_rename_by_name_name_already_exists_error(env_one, conda_cli):
    """Test to ensure that we do not rename if the name already exists"""
    with pytest.raises(CondaEnvException) as exc:
        conda_cli(["rename", "-p", TEST_ENV_NAME_1, TEST_ENV_NAME_1])
        assert "Environment destination already exists" in str(exc)


def test_rename_by_path_path_already_exists_error(env_one, conda_cli):
    """Test to ensure that we do not rename if the path already exists"""
    with tempfile.TemporaryDirectory() as tempdir:
        with pytest.raises(CondaEnvException) as exc:
            conda_cli(["rename", "-p", TEST_ENV_NAME_1, tempdir])
            assert "Environment destination already exists" in str(exc)


def test_rename_base_env_by_name_error(env_one, conda_cli):
    """Test to ensure that we cannot rename the base env invoked by name"""
    with pytest.raises(CondaEnvException) as exc:
        conda_cli(["rename", "-n", "base", TEST_ENV_NAME_RENAME])
        assert "The 'base' environment cannot be renamed" in str(exc)


def test_rename_base_env_by_path_error(env_one, conda_cli):
    """Test to ensure that we cannot rename the base env invoked by path"""
    with pytest.raises(CondaEnvException) as exc:
        conda_cli(["rename", "-p", context.root_prefix, TEST_ENV_NAME_RENAME])
        assert "The 'base' environment cannot be renamed" in str(exc)


def test_rename_with_force(env_one, env_two, conda_cli, conda_env_cli):
    """
    Runs a test where we specify the --force flag to remove an existing directory.
    Without this flag, it would return with an error message.
    """
    # Do a force rename
    conda_cli(["rename", "-n", TEST_ENV_NAME_1, TEST_ENV_NAME_2, "--force"])

    res, data = list_envs(conda_env_cli)
    result = data.get("envs", [])

    # Clean up
    conda_cli(["rename", "-n", TEST_ENV_NAME_2, TEST_ENV_NAME_1])

    rename_appears_in_envs = any(path.endswith(TEST_ENV_NAME_2) for path in result)
    force_name_not_in_envs = not any(path.endswith(TEST_ENV_NAME_1) for path in result)

    assert rename_appears_in_envs
    assert force_name_not_in_envs
    assert res.err == ""


def test_rename_with_dry_run(env_one, conda_cli, conda_env_cli):
    """
    Runs a test where we specify the --dry-run flag to remove an existing directory.
    Without this flag, it would actually execute all the actions.
    """
    rename_res = conda_cli(["rename", "-n", TEST_ENV_NAME_1, TEST_ENV_NAME_RENAME, "--dry-run"])

    res, data = list_envs(conda_env_cli)
    result = data.get("envs", [])

    rename_appears_in_envs = any(path.endswith(TEST_ENV_NAME_1) for path in result)
    force_name_not_in_envs = not any(path.endswith(TEST_ENV_NAME_RENAME) for path in result)

    assert rename_appears_in_envs
    assert force_name_not_in_envs
    assert res.err == ""

    rename_stdout = str(rename_res.out)
    assert "Dry run action: clone" in rename_stdout
    assert "Dry run action: rm_rf" in rename_stdout
    assert rename_res.err == ""
