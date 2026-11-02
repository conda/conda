# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Tests for the missing files health check.

Note: env_ok, env_missing_files fixtures are defined in
tests/plugins/subcommands/conftest.py and shared with health fix tests.
"""

from __future__ import annotations

import json
from argparse import Namespace
from typing import TYPE_CHECKING

import pytest

from conda.plugins.subcommands.doctor.health_checks.missing_files import (
    find_packages_with_missing_files,
    fix_missing_files,
    missing_files,
)

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from tests.plugins.subcommands.conftest import EnvFixture


def test_no_missing_files(env_ok: EnvFixture):
    """Test that runs for the case with no missing files."""
    assert find_packages_with_missing_files(env_ok.prefix) == {}


def test_missing_files(env_missing_files: EnvFixture):
    """Test that missing files are detected correctly."""
    assert find_packages_with_missing_files(env_missing_files.prefix) == {
        env_missing_files.package: [env_missing_files.bin_file]
    }


@pytest.mark.parametrize("verbose", [True, False])
def test_missing_files_action(env_missing_files: EnvFixture, capsys, verbose):
    """Test the missing_files action output."""
    missing_files(env_missing_files.prefix, verbose=verbose)
    captured = capsys.readouterr()
    if verbose:
        assert str(env_missing_files.bin_file) in captured.out
        assert str(env_missing_files.ignored_file) not in captured.out
    else:
        assert f"{env_missing_files.package}: 1" in captured.out


@pytest.mark.parametrize("verbose", [True, False])
def test_no_missing_files_action(env_ok: EnvFixture, capsys, verbose):
    """Test the missing_files action when there are no missing files."""
    missing_files(env_ok.prefix, verbose=verbose)
    captured = capsys.readouterr()
    assert "There are no packages with missing files." in captured.out


def test_fix_missing_files_skips_reinstall(
    env_missing_files: EnvFixture,
    mocker: MockerFixture,
    capsys: pytest.CaptureFixture,
):
    """Packages whose conda-meta record lacks a build are skipped, not reinstalled."""
    (env_missing_files.prefix / "conda-meta" / "bad-2.0-0kjd.json").write_text(
        json.dumps(
            {
                "name": "bad",
                "version": "2.0",
                "files": ["bin/bad"],
            }
        )
    )

    mock_reinstall = mocker.patch(
        "conda.plugins.subcommands.doctor.health_checks.missing_files.reinstall_packages",
        return_value=0,
    )
    confirm = mocker.Mock()
    args = Namespace()

    result = fix_missing_files(str(env_missing_files.prefix), args, confirm)
    assert result == 1
    confirm.assert_called_once()
    mock_reinstall.assert_called_once()
    assert ("Reinstalling bad was skipped") in capsys.readouterr().out
