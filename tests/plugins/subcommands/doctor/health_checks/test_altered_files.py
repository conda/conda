# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Tests for the altered files health check.

Note: env_ok, env_altered_files fixtures are defined in
tests/plugins/subcommands/conftest.py and shared with health fix tests.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from conda.plugins.subcommands.doctor.health_checks import (
    altered_files,
    find_altered_packages,
)

if TYPE_CHECKING:
    from pathlib import Path


def test_no_altered_files(env_ok: tuple[Path, str, str, str, str]):
    """Test that runs for the case with no altered files."""
    prefix, _, _, _, _ = env_ok
    assert find_altered_packages(prefix) == {}


def test_altered_files(env_altered_files: tuple[Path, str, str, str, str]):
    """Test that altered files are detected correctly."""
    prefix, _, lib_file, _, package = env_altered_files
    assert find_altered_packages(prefix) == {package: [lib_file]}


@pytest.mark.parametrize("verbose", [True, False])
def test_altered_files_action(
    env_altered_files: tuple[Path, str, str, str, str], capsys, verbose
):
    """Test the altered_files action output."""
    prefix, _, lib_file, ignored_file, package = env_altered_files
    altered_files(prefix, verbose=verbose)
    captured = capsys.readouterr()
    if verbose:
        assert str(lib_file) in captured.out
        assert str(ignored_file) not in captured.out
    else:
        assert f"{package}: 1" in captured.out


@pytest.mark.parametrize("verbose", [True, False])
def test_no_altered_files_action(
    env_ok: tuple[Path, str, str, str, str], capsys, verbose
):
    """Test the altered_files action when there are no altered files."""
    prefix, _, _, _, _ = env_ok
    altered_files(prefix, verbose=verbose)
    captured = capsys.readouterr()
    assert "There are no packages with altered files." in captured.out


def test_json_keys_missing(env_ok: tuple[Path, str, str, str, str], capsys):
    """Test that runs for the case with empty json."""
    prefix, _, _, _, package = env_ok
    file = prefix / "conda-meta" / f"{package}.json"
    with open(file) as f:
        data = json.load(f)
    del data["paths_data"]
    with open(file, "w") as f:
        json.dump(data, f)

    assert find_altered_packages(prefix) == {}


def test_wrong_path_version(env_ok: tuple[Path, str, str, str, str]):
    """Test that runs for the case when path_version is not equal to 1."""
    prefix, _, _, _, package = env_ok
    file = prefix / "conda-meta" / f"{package}.json"
    with open(file) as f:
        data = json.load(f)
        data["paths_data"]["paths_version"] = 2
    with open(file, "w") as f:
        json.dump(data, f)

    assert find_altered_packages(prefix) == {}


def test_json_cannot_be_loaded(env_ok: tuple[Path, str, str, str, str]):
    """Test that runs for the case when json file is missing."""
    prefix, _, _, _, package = env_ok
    # passing a None type to json.loads() so that it fails
    assert find_altered_packages(prefix) == {}

