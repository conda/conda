# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Tests for the malformed-pinned fix task."""

from __future__ import annotations

from argparse import Namespace
from typing import TYPE_CHECKING

from conda.base.constants import PREFIX_PINNED_FILE
from conda.plugins.subcommands.fix.health_fixes import malformed_pinned

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture


def test_no_pinned_file(
    tmp_path: Path,
    mocker: MockerFixture,
    capsys,
):
    """Test when there is no pinned file."""
    prefix = tmp_path / "env"
    prefix.mkdir()
    (prefix / "conda-meta").mkdir()

    mock_prefix_data = mocker.MagicMock()
    mock_prefix_data.prefix_path = prefix
    mock_prefix_data.assert_environment = mocker.MagicMock()
    mocker.patch(
        "conda.plugins.subcommands.fix.health_fixes.malformed_pinned.PrefixData.from_context",
        return_value=mock_prefix_data,
    )

    args = Namespace()
    result = malformed_pinned.execute(args)

    assert result == 0
    captured = capsys.readouterr()
    assert "No pinned file found" in captured.out


def test_empty_pinned_file(
    tmp_path: Path,
    mocker: MockerFixture,
    capsys,
):
    """Test when pinned file is empty."""
    prefix = tmp_path / "env"
    prefix.mkdir()
    (prefix / "conda-meta").mkdir()
    (prefix / PREFIX_PINNED_FILE).write_text("")

    mock_prefix_data = mocker.MagicMock()
    mock_prefix_data.prefix_path = prefix
    mock_prefix_data.get_pinned_specs.return_value = []
    mock_prefix_data.assert_environment = mocker.MagicMock()
    mocker.patch(
        "conda.plugins.subcommands.fix.health_fixes.malformed_pinned.PrefixData.from_context",
        return_value=mock_prefix_data,
    )

    args = Namespace()
    result = malformed_pinned.execute(args)

    assert result == 0
    captured = capsys.readouterr()
    assert "Pinned file is empty." in captured.out


def test_no_malformed_specs(
    tmp_path: Path,
    mocker: MockerFixture,
    capsys,
):
    """Test when all pinned specs are valid."""
    prefix = tmp_path / "env"
    prefix.mkdir()
    (prefix / "conda-meta").mkdir()
    (prefix / PREFIX_PINNED_FILE).write_text("python >=3.9")

    mock_spec = mocker.MagicMock()
    mock_spec.name = "python"

    mock_prefix_data = mocker.MagicMock()
    mock_prefix_data.prefix_path = prefix
    mock_prefix_data.get_pinned_specs.return_value = [mock_spec]
    mock_prefix_data.query.return_value = [mocker.MagicMock()]  # Package exists
    mock_prefix_data.assert_environment = mocker.MagicMock()
    mocker.patch(
        "conda.plugins.subcommands.fix.health_fixes.malformed_pinned.PrefixData.from_context",
        return_value=mock_prefix_data,
    )

    args = Namespace()
    result = malformed_pinned.execute(args)

    assert result == 0
    captured = capsys.readouterr()
    assert "No malformed specs found" in captured.out


def test_with_malformed_specs(
    tmp_path: Path,
    mocker: MockerFixture,
    capsys,
):
    """Test when there are malformed specs in the pinned file."""
    prefix = tmp_path / "env"
    prefix.mkdir()
    (prefix / "conda-meta").mkdir()
    pinned_file = prefix / PREFIX_PINNED_FILE
    pinned_file.write_text("# comment\nnotinstalled >=1.0\npython >=3.9\n")

    mock_spec_bad = mocker.MagicMock()
    mock_spec_bad.name = "notinstalled"
    mock_spec_bad.__str__ = lambda self: "notinstalled >=1.0"

    mock_spec_good = mocker.MagicMock()
    mock_spec_good.name = "python"
    mock_spec_good.__str__ = lambda self: "python >=3.9"

    mock_prefix_data = mocker.MagicMock()
    mock_prefix_data.prefix_path = prefix
    mock_prefix_data.get_pinned_specs.return_value = [mock_spec_bad, mock_spec_good]
    mock_prefix_data.assert_environment = mocker.MagicMock()
    mock_prefix_data.query.side_effect = (
        lambda name: [] if name == "notinstalled" else [mocker.MagicMock()]
    )
    mocker.patch(
        "conda.plugins.subcommands.fix.health_fixes.malformed_pinned.PrefixData.from_context",
        return_value=mock_prefix_data,
    )

    mock_confirm = mocker.patch(
        "conda.plugins.subcommands.fix.health_fixes.malformed_pinned.confirm_yn"
    )
    mocker.patch(
        "conda.plugins.subcommands.fix.health_fixes.malformed_pinned.context"
    ).dry_run = False

    args = Namespace(dry_run=False)
    result = malformed_pinned.execute(args)

    assert result == 0
    mock_confirm.assert_called_once()

    captured = capsys.readouterr()
    assert "Found 1 potentially malformed spec(s)" in captured.out
    assert "notinstalled" in captured.out

