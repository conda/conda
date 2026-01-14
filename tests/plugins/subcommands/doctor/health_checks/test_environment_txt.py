# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Tests for the environment.txt health check.

Note: env_ok fixture is defined in tests/plugins/subcommands/conftest.py
and shared with health fix tests.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from conda.base.constants import OK_MARK, X_MARK
from conda.plugins.subcommands.doctor.health_checks.environment_txt import (
    check_envs_txt_file,
    env_txt_check,
)

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture

    from tests.plugins.subcommands.conftest import EnvFixture


def test_listed_on_envs_txt_file(
    tmp_path: Path, mocker: MockerFixture, env_ok: EnvFixture
):
    """Test that runs for the case when the env is listed on the environments.txt file."""
    tmp_envs_txt_file = tmp_path / "envs.txt"
    tmp_envs_txt_file.write_text(f"{env_ok.prefix}")

    mocker.patch(
        "conda.plugins.subcommands.doctor.health_checks.environment_txt.get_user_environments_txt_file",
        return_value=tmp_envs_txt_file,
    )
    assert check_envs_txt_file(env_ok.prefix)


def test_not_listed_on_envs_txt_file(
    tmp_path: Path, mocker: MockerFixture, env_ok: EnvFixture
):
    """Test that runs for the case when the env is not listed on the environments.txt file."""
    tmp_envs_txt_file = tmp_path / "envs.txt"
    tmp_envs_txt_file.write_text("Not environment name")

    mocker.patch(
        "conda.plugins.subcommands.doctor.health_checks.environment_txt.get_user_environments_txt_file",
        return_value=tmp_envs_txt_file,
    )
    assert not check_envs_txt_file(env_ok.prefix)


def test_env_txt_check_action(
    tmp_path: Path, mocker: MockerFixture, env_ok: EnvFixture, capsys
):
    """Test the env_txt_check action when the environment is registered."""
    tmp_envs_txt_file = tmp_path / "envs.txt"
    tmp_envs_txt_file.write_text(f"{env_ok.prefix}")

    mocker.patch(
        "conda.plugins.subcommands.doctor.health_checks.environment_txt.get_user_environments_txt_file",
        return_value=tmp_envs_txt_file,
    )
    env_txt_check(env_ok.prefix, verbose=True)
    captured = capsys.readouterr()
    assert OK_MARK in captured.out


def test_not_env_txt_check_action(
    tmp_path: Path, mocker: MockerFixture, env_ok: EnvFixture, capsys
):
    """Test the env_txt_check action when the environment is not registered."""
    tmp_envs_txt_file = tmp_path / "envs.txt"
    tmp_envs_txt_file.write_text("Not environment name")

    mocker.patch(
        "conda.plugins.subcommands.doctor.health_checks.environment_txt.get_user_environments_txt_file",
        return_value=tmp_envs_txt_file,
    )
    env_txt_check(env_ok.prefix, verbose=True)
    captured = capsys.readouterr()
    assert X_MARK in captured.out
