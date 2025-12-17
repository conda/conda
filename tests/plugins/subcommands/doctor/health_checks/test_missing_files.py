# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Tests for the missing files health check.

Note: env_ok, env_missing_files fixtures are defined in
tests/plugins/subcommands/conftest.py and shared with health fix tests.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from conda.plugins.subcommands.doctor.health_checks import (
    find_packages_with_missing_files,
    missing_files,
)

if TYPE_CHECKING:
    from pathlib import Path


def test_no_missing_files(env_ok: tuple[Path, str, str, str, str]):
    """Test that runs for the case with no missing files."""
    prefix, _, _, _, _ = env_ok
    assert find_packages_with_missing_files(prefix) == {}


def test_missing_files(env_missing_files: tuple[Path, str, str, str, str]):
    """Test that missing files are detected correctly."""
    prefix, bin_file, _, ignored_file, package = env_missing_files
    assert find_packages_with_missing_files(prefix) == {package: [bin_file]}


@pytest.mark.parametrize("verbose", [True, False])
def test_missing_files_action(
    env_missing_files: tuple[Path, str, str, str, str], capsys, verbose
):
    """Test the missing_files action output."""
    prefix, bin_file, _, ignored_file, package = env_missing_files
    missing_files(prefix, verbose=verbose)
    captured = capsys.readouterr()
    if verbose:
        assert str(bin_file) in captured.out
        assert str(ignored_file) not in captured.out
    else:
        assert f"{package}: 1" in captured.out


@pytest.mark.parametrize("verbose", [True, False])
def test_no_missing_files_action(
    env_ok: tuple[Path, str, str, str, str], capsys, verbose
):
    """Test the missing_files action when there are no missing files."""
    prefix, _, _, _, _ = env_ok
    missing_files(prefix, verbose=verbose)
    captured = capsys.readouterr()
    assert "There are no packages with missing files." in captured.out
