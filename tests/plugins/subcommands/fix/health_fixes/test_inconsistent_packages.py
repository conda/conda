# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Tests for the inconsistent-packages fix task."""

from __future__ import annotations

from argparse import Namespace
from typing import TYPE_CHECKING

from conda.plugins.subcommands.fix.health_fixes import inconsistent_packages

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture


def test_no_inconsistencies(
    tmp_path: Path,
    mocker: MockerFixture,
    capsys,
):
    """Test when no packages have inconsistencies."""
    prefix = tmp_path / "env"
    prefix.mkdir()
    (prefix / "conda-meta").mkdir()

    mock_prefix_data = mocker.MagicMock()
    mock_prefix_data.prefix_path = prefix
    mock_prefix_data.iter_records.return_value = []
    mock_prefix_data.assert_environment = mocker.MagicMock()
    mocker.patch(
        "conda.plugins.subcommands.fix.health_fixes.inconsistent_packages.PrefixData.from_context",
        return_value=mock_prefix_data,
    )

    mock_context = mocker.patch(
        "conda.plugins.subcommands.fix.health_fixes.inconsistent_packages.context"
    )
    mock_context.plugin_manager.get_virtual_package_records.return_value = []

    args = Namespace()
    result = inconsistent_packages.execute(args)

    assert result == 0
    captured = capsys.readouterr()
    assert "No inconsistent packages found." in captured.out
