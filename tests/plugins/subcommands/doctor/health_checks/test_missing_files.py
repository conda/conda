# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Tests for the missing files health check.

Note: env_ok, env_missing_files fixtures are defined in
tests/plugins/subcommands/conftest.py and shared with health fix tests.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from conda.plugins.subcommands.doctor.health_checks.missing_files import (
    find_packages_with_missing_files,
    missing_files,
)

if TYPE_CHECKING:
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
