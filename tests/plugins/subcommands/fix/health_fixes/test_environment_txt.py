# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Tests for the environment-txt fix task."""

from __future__ import annotations

from argparse import Namespace
from typing import TYPE_CHECKING

from conda.plugins.subcommands.fix.health_fixes import environment_txt

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture


def test_already_registered(
    tmp_path: Path,
    mocker: MockerFixture,
    capsys,
):
    """Test when environment is already registered."""
    prefix = tmp_path / "env"
    prefix.mkdir()
    (prefix / "conda-meta").mkdir()

    mock_prefix_data = mocker.MagicMock()
    mock_prefix_data.prefix_path = prefix
    mock_prefix_data.assert_environment = mocker.MagicMock()
    mocker.patch(
        "conda.plugins.subcommands.fix.health_fixes.environment_txt.PrefixData.from_context",
        return_value=mock_prefix_data,
    )

    mocker.patch(
        "conda.plugins.subcommands.fix.health_fixes.environment_txt.check_envs_txt_file",
        return_value=True,
    )

    args = Namespace()
    result = environment_txt.execute(args)

    assert result == 0
    captured = capsys.readouterr()
    assert "already registered" in captured.out


def test_not_registered(
    tmp_path: Path,
    mocker: MockerFixture,
    capsys,
):
    """Test when environment is not registered and gets registered."""
    prefix = tmp_path / "env"
    prefix.mkdir()
    (prefix / "conda-meta").mkdir()

    envs_txt = tmp_path / "envs.txt"
    envs_txt.write_text("")

    mock_prefix_data = mocker.MagicMock()
    mock_prefix_data.prefix_path = prefix
    mock_prefix_data.assert_environment = mocker.MagicMock()
    mocker.patch(
        "conda.plugins.subcommands.fix.health_fixes.environment_txt.PrefixData.from_context",
        return_value=mock_prefix_data,
    )

    mocker.patch(
        "conda.plugins.subcommands.fix.health_fixes.environment_txt.check_envs_txt_file",
        return_value=False,
    )
    mocker.patch(
        "conda.plugins.subcommands.fix.health_fixes.environment_txt.get_user_environments_txt_file",
        return_value=envs_txt,
    )

    mock_confirm = mocker.patch(
        "conda.plugins.subcommands.fix.health_fixes.environment_txt.confirm_yn"
    )
    mock_register = mocker.patch(
        "conda.plugins.subcommands.fix.health_fixes.environment_txt.register_env"
    )

    args = Namespace(dry_run=False)
    result = environment_txt.execute(args)

    assert result == 0
    mock_confirm.assert_called_once()
    mock_register.assert_called_once_with(str(prefix))

    captured = capsys.readouterr()
    assert "Environment registered" in captured.out

