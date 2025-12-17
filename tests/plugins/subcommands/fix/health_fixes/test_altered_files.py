# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Tests for the altered-files fix task."""

from __future__ import annotations

from argparse import Namespace
from typing import TYPE_CHECKING

from conda.plugins.subcommands.fix.health_fixes import altered_files

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture


def test_no_altered_files(
    env_ok: tuple[Path, str, str, str, str],
    mocker: MockerFixture,
    capsys,
):
    """Test when no packages have altered files."""
    prefix, _, _, _, _ = env_ok

    mock_prefix_data = mocker.MagicMock()
    mock_prefix_data.prefix_path = prefix
    mock_prefix_data.assert_environment = mocker.MagicMock()
    mocker.patch(
        "conda.plugins.subcommands.fix.health_fixes.altered_files.PrefixData.from_context",
        return_value=mock_prefix_data,
    )

    mocker.patch(
        "conda.plugins.subcommands.fix.health_fixes.altered_files.find_altered_packages",
        return_value={},
    )

    args = Namespace()
    result = altered_files.execute(args)

    assert result == 0
    captured = capsys.readouterr()
    assert "No packages with altered files found." in captured.out


def test_with_altered_files(
    env_altered_files: tuple[Path, str, str, str, str],
    mocker: MockerFixture,
    capsys,
):
    """Test when packages have altered files."""
    prefix, _, lib_file, _, package = env_altered_files

    mock_prefix_data = mocker.MagicMock()
    mock_prefix_data.prefix_path = prefix
    mock_prefix_data.assert_environment = mocker.MagicMock()
    mocker.patch(
        "conda.plugins.subcommands.fix.health_fixes.altered_files.PrefixData.from_context",
        return_value=mock_prefix_data,
    )

    mocker.patch(
        "conda.plugins.subcommands.fix.health_fixes.altered_files.find_altered_packages",
        return_value={package: [lib_file]},
    )

    mock_confirm = mocker.patch(
        "conda.plugins.subcommands.fix.health_fixes.altered_files.confirm_yn"
    )
    mock_install = mocker.patch(
        "conda.cli.install.install",
        return_value=0,
    )

    args = Namespace(dry_run=False)
    result = altered_files.execute(args)

    assert result == 0
    mock_confirm.assert_called_once()
    mock_install.assert_called_once()
    assert args.packages == [package]
    assert args.force_reinstall is True

    captured = capsys.readouterr()
    assert "Found 1 package(s) with altered files:" in captured.out
