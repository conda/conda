# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Tests for the altered files health check.

Note: env_ok, env_altered_files fixtures are defined in
tests/plugins/subcommands/conftest.py and shared with health fix tests.
"""

from __future__ import annotations

import json
from argparse import Namespace
from typing import TYPE_CHECKING

import pytest

from conda.plugins.subcommands.doctor.health_checks.altered_files import (
    altered_files,
    find_altered_packages,
    fix_altered_files,
)

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from tests.plugins.subcommands.conftest import EnvFixture


def test_no_altered_files(env_ok: EnvFixture):
    """Test that runs for the case with no altered files."""
    assert find_altered_packages(env_ok.prefix) == {}


def test_altered_files(env_altered_files: EnvFixture):
    """Test that altered files are detected correctly."""
    assert find_altered_packages(env_altered_files.prefix) == {
        env_altered_files.package: [env_altered_files.lib_file]
    }


@pytest.mark.parametrize("verbose", [True, False])
def test_altered_files_action(env_altered_files: EnvFixture, capsys, verbose):
    """Test the altered_files action output."""
    altered_files(env_altered_files.prefix, verbose=verbose)
    captured = capsys.readouterr()
    if verbose:
        assert str(env_altered_files.lib_file) in captured.out
        assert str(env_altered_files.ignored_file) not in captured.out
    else:
        assert f"{env_altered_files.package}: 1" in captured.out


@pytest.mark.parametrize("verbose", [True, False])
def test_no_altered_files_action(env_ok: EnvFixture, capsys, verbose):
    """Test the altered_files action when there are no altered files."""
    altered_files(env_ok.prefix, verbose=verbose)
    captured = capsys.readouterr()
    assert "There are no packages with altered files." in captured.out


def test_json_keys_missing(env_ok: EnvFixture, capsys):
    """Test that runs for the case with empty json."""
    file = env_ok.prefix / "conda-meta" / f"{env_ok.package}.json"
    with open(file) as f:
        data = json.load(f)
    del data["paths_data"]
    with open(file, "w") as f:
        json.dump(data, f)

    assert find_altered_packages(env_ok.prefix) == {}


def test_wrong_path_version(env_ok: EnvFixture):
    """Test that runs for the case when path_version is not equal to 1."""
    file = env_ok.prefix / "conda-meta" / f"{env_ok.package}.json"
    with open(file) as f:
        data = json.load(f)
        data["paths_data"]["paths_version"] = 2
    with open(file, "w") as f:
        json.dump(data, f)

    assert find_altered_packages(env_ok.prefix) == {}


def test_json_cannot_be_loaded(env_ok: EnvFixture):
    """Test that runs for the case when json file is missing."""
    # passing a None type to json.loads() so that it fails
    assert find_altered_packages(env_ok.prefix) == {}


def test_fix_altered_files_skips_reinstall(
    env_altered_files: EnvFixture,
    mocker: MockerFixture,
    capsys: pytest.CaptureFixture,
):
    """Packages whose conda-meta record lacks a build are skipped, not reinstalled."""
    file = env_altered_files.prefix / "conda-meta" / f"{env_altered_files.package}.json"
    with open(file) as f:
        data = json.load(f)
        del data["build"]
    with open(file, "w") as f:
        json.dump(data, f)

    mock_reinstall = mocker.patch(
        "conda.plugins.subcommands.doctor.health_checks.altered_files.reinstall_packages",
        return_value=0,
    )
    confirm = mocker.Mock()
    args = Namespace()

    result = fix_altered_files(str(env_altered_files.prefix), args, confirm)

    assert result == 1
    confirm.assert_called_once()
    mock_reinstall.assert_not_called()
    assert (
        f"Reinstalling {env_altered_files.package} was skipped"
    ) in capsys.readouterr().out
