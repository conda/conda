# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Tests for the `conda fix` subcommand."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from conda.testing.fixtures import CondaCLIFixture, TmpEnvFixture


def test_conda_fix_help(conda_cli: CondaCLIFixture):
    """Make sure that we are able to run `conda fix --help`."""
    with pytest.raises(SystemExit, match="0"):
        conda_cli("fix", "--help")


def test_conda_fix_list(conda_cli: CondaCLIFixture):
    """Make sure that we are able to run `conda fix --list`."""
    out, err, code = conda_cli("fix", "--list")

    assert "Available health fixes:" in out
    assert not err
    assert not code


def test_conda_fix_list_json(conda_cli: CondaCLIFixture):
    """Make sure that `conda fix --list --json` returns valid JSON."""
    import json

    out, err, code = conda_cli("fix", "--list", "--json")

    # Should be valid JSON (list of health fixes)
    health_fixes = json.loads(out)
    assert isinstance(health_fixes, list)
    assert not code


def test_conda_fix_no_health_fix_error(conda_cli: CondaCLIFixture):
    """Make sure that `conda fix` without a health fix shows an error."""
    from conda.exceptions import CondaError

    out, err, exc = conda_cli("fix", raises=CondaError)

    assert exc
    assert "No health fix specified" in str(exc)


def test_conda_fix_dry_run_option(conda_cli: CondaCLIFixture):
    """Test that --dry-run option is accepted."""
    out, err, code = conda_cli("fix", "--list", "--dry-run")

    assert "Available health fixes:" in out
    assert not code


def test_conda_fix_yes_option(conda_cli: CondaCLIFixture):
    """Test that --yes option is accepted."""
    out, err, code = conda_cli("fix", "--list", "--yes")

    assert "Available health fixes:" in out
    assert not code


# ==========================
# Health fix CLI tests
# ==========================


def test_fix_missing_files_help(conda_cli: CondaCLIFixture):
    """Test conda fix missing-files --help."""
    with pytest.raises(SystemExit, match="0"):
        conda_cli("fix", "missing-files", "--help")


def test_fix_altered_files_help(conda_cli: CondaCLIFixture):
    """Test conda fix altered-files --help."""
    with pytest.raises(SystemExit, match="0"):
        conda_cli("fix", "altered-files", "--help")


def test_fix_environment_txt_help(conda_cli: CondaCLIFixture):
    """Test conda fix environment-txt --help."""
    with pytest.raises(SystemExit, match="0"):
        conda_cli("fix", "environment-txt", "--help")


def test_fix_inconsistent_packages_help(conda_cli: CondaCLIFixture):
    """Test conda fix inconsistent-packages --help."""
    with pytest.raises(SystemExit, match="0"):
        conda_cli("fix", "inconsistent-packages", "--help")


def test_fix_malformed_pinned_help(conda_cli: CondaCLIFixture):
    """Test conda fix malformed-pinned --help."""
    with pytest.raises(SystemExit, match="0"):
        conda_cli("fix", "malformed-pinned", "--help")


def test_fix_missing_files_no_issues(
    tmp_env: TmpEnvFixture,
    conda_cli: CondaCLIFixture,
):
    """Test conda fix missing-files when no files are missing."""
    with tmp_env() as prefix:
        out, err, code = conda_cli("fix", "missing-files", "--prefix", prefix)
        assert code == 0
        assert "No packages with missing files found" in out


def test_fix_altered_files_no_issues(
    tmp_env: TmpEnvFixture,
    conda_cli: CondaCLIFixture,
):
    """Test conda fix altered-files when no files are altered."""
    with tmp_env() as prefix:
        out, err, code = conda_cli("fix", "altered-files", "--prefix", prefix)
        assert code == 0
        assert "No packages with altered files found" in out


def test_fix_inconsistent_packages_no_issues(
    tmp_env: TmpEnvFixture,
    conda_cli: CondaCLIFixture,
):
    """Test conda fix inconsistent-packages when no inconsistencies."""
    with tmp_env() as prefix:
        out, err, code = conda_cli("fix", "inconsistent-packages", "--prefix", prefix)
        assert code == 0
        assert "No inconsistent packages found" in out


def test_fix_malformed_pinned_no_file(
    tmp_env: TmpEnvFixture,
    conda_cli: CondaCLIFixture,
):
    """Test conda fix malformed-pinned when no pinned file exists."""
    with tmp_env() as prefix:
        out, err, code = conda_cli("fix", "malformed-pinned", "--prefix", prefix)
        assert code == 0
        assert "No pinned file found" in out
