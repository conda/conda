# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Tests for the environment.txt health check.

Note: env_ok fixture is defined in tests/plugins/subcommands/conftest.py
and shared with health fix tests.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from conda.plugins.subcommands.doctor.health_checks import (
    OK_MARK,
    X_MARK,
    check_envs_txt_file,
    env_txt_check,
)

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture


def test_listed_on_envs_txt_file(
    tmp_path: Path, mocker: MockerFixture, env_ok: tuple[Path, str, str, str, str]
):
    """Test that runs for the case when the env is listed on the environments.txt file."""
    prefix, _, _, _, _ = env_ok
    tmp_envs_txt_file = tmp_path / "envs.txt"
    tmp_envs_txt_file.write_text(f"{prefix}")

    mocker.patch(
        "conda.plugins.subcommands.doctor.health_checks.get_user_environments_txt_file",
        return_value=tmp_envs_txt_file,
    )
    assert check_envs_txt_file(prefix)


def test_not_listed_on_envs_txt_file(
    tmp_path: Path, mocker: MockerFixture, env_ok: tuple[Path, str, str, str, str]
):
    """Test that runs for the case when the env is not listed on the environments.txt file."""
    prefix, _, _, _, _ = env_ok
    tmp_envs_txt_file = tmp_path / "envs.txt"
    tmp_envs_txt_file.write_text("Not environment name")

    mocker.patch(
        "conda.plugins.subcommands.doctor.health_checks.get_user_environments_txt_file",
        return_value=tmp_envs_txt_file,
    )
    assert not check_envs_txt_file(prefix)


def test_env_txt_check_action(
    tmp_path: Path,
    mocker: MockerFixture,
    env_ok: tuple[Path, str, str, str, str],
    capsys,
):
    """Test the env_txt_check action when the environment is registered."""
    prefix, _, _, _, _ = env_ok
    tmp_envs_txt_file = tmp_path / "envs.txt"
    tmp_envs_txt_file.write_text(f"{prefix}")

    mocker.patch(
        "conda.plugins.subcommands.doctor.health_checks.get_user_environments_txt_file",
        return_value=tmp_envs_txt_file,
    )
    env_txt_check(prefix, verbose=True)
    captured = capsys.readouterr()
    assert OK_MARK in captured.out


def test_not_env_txt_check_action(
    tmp_path: Path,
    mocker: MockerFixture,
    env_ok: tuple[Path, str, str, str, str],
    capsys,
):
    """Test the env_txt_check action when the environment is not registered."""
    prefix, _, _, _, _ = env_ok
    tmp_envs_txt_file = tmp_path / "envs.txt"
    tmp_envs_txt_file.write_text("Not environment name")

    mocker.patch(
        "conda.plugins.subcommands.doctor.health_checks.get_user_environments_txt_file",
        return_value=tmp_envs_txt_file,
    )
    env_txt_check(prefix, verbose=True)
    captured = capsys.readouterr()
    assert X_MARK in captured.out

