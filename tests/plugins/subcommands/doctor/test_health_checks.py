# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Iterable

import pytest
from pytest import MonkeyPatch
from pytest_mock import MockerFixture

from conda.base.context import reset_context
from conda.common.io import env_vars
from conda.plugins.subcommands.doctor.health_checks import (
    check_envs_txt_file,
    display_health_checks,
    find_altered_packages,
    find_packages_with_missing_files,
)
from conda.testing.integration import make_temp_env


@pytest.fixture
def env_ok(tmp_path: Path) -> Iterable[tuple[Path, str, str, str]]:
    """Fixture that returns a testing environment with no missing files"""
    package = uuid.uuid4().hex

    (tmp_path / "bin").mkdir(parents=True, exist_ok=True)
    (tmp_path / "lib").mkdir(parents=True, exist_ok=True)
    (tmp_path / "conda-meta").mkdir(parents=True, exist_ok=True)

    bin_doctor = f"bin/{package}"
    (tmp_path / bin_doctor).touch()

    lib_doctor = f"lib/{package}.py"
    (tmp_path / lib_doctor).touch()

    # A template json file mimicking a json file in conda-meta
    # the "sha256" and "sha256_in_prefix" values are sha256 checksum generated for an empty file
    PACKAGE_JSON = {
        "files": [
            bin_doctor,
            lib_doctor,
        ],
        "paths_data": {
            "paths": [
                {
                    "_path": bin_doctor,
                    "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                    "sha256_in_prefix": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                },
                {
                    "_path": lib_doctor,
                    "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                    "sha256_in_prefix": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                },
            ],
            "paths_version": 1,
        },
    }

    (tmp_path / "conda-meta" / f"{package}.json").write_text(json.dumps(PACKAGE_JSON))

    yield tmp_path, bin_doctor, lib_doctor, package


@pytest.fixture
def env_missing_files(env_ok: tuple[Path, str, str, str]) -> tuple[Path, str, str, str]:
    """Fixture that returns a testing environment with missing files"""
    prefix, bin_doctor, _, _ = env_ok
    (prefix / bin_doctor).unlink()  # file bin_doctor becomes "missing"
    return env_ok


@pytest.fixture
def env_altered_files(env_ok: tuple[Path, str, str, str]) -> tuple[Path, str, str, str]:
    """Fixture that returns a testing environment with altered files"""
    prefix, _, lib_doctor, _ = env_ok
    # Altering the lib_doctor.py file so that it's sha256 checksum will change
    with open(prefix / lib_doctor, "w") as f:
        f.write("print('Hello, World!')")

    return env_ok


def test_listed_on_envs_txt_file(
    tmp_path: Path, mocker: MockerFixture, env_ok: tuple[Path, str, str, str]
):
    """Test that runs for the case when the env is listed on the environments.txt file"""
    prefix, _, _, _ = env_ok
    tmp_envs_txt_file = tmp_path / "envs.txt"
    tmp_envs_txt_file.write_text(f"{prefix}")

    mocker.patch(
        "conda.plugins.subcommands.doctor.health_checks.get_user_environments_txt_file",
        return_value=tmp_envs_txt_file,
    )
    assert check_envs_txt_file(prefix)


def test_not_listed_on_envs_txt_file(
    tmp_path: Path, mocker: MockerFixture, env_ok: tuple[Path, str, str, str]
):
    """Test that runs for the case when the env is not listed on the environments.txt file"""
    prefix, _, _, _ = env_ok
    tmp_envs_txt_file = tmp_path / "envs.txt"
    tmp_envs_txt_file.write_text("Not environment name")

    mocker.patch(
        "conda.plugins.subcommands.doctor.health_checks.get_user_environments_txt_file",
        return_value=tmp_envs_txt_file,
    )
    assert not check_envs_txt_file(prefix)


def test_no_missing_files(env_ok: tuple[Path, str, str, str]):
    """Test that runs for the case with no missing files"""
    prefix, _, _, _ = env_ok
    assert find_packages_with_missing_files(prefix) == {}


def test_missing_files(env_missing_files: tuple[Path, str, str, str]):
    prefix, bin_doctor, _, package = env_missing_files
    assert find_packages_with_missing_files(prefix) == {package: [bin_doctor]}


def test_no_altered_files(env_ok: tuple[Path, str, str, str]):
    """Test that runs for the case with no altered files"""
    prefix, _, _, _ = env_ok
    assert find_altered_packages(prefix) == {}


def test_altered_files(env_altered_files: tuple[Path, str, str, str]):
    prefix, _, lib_doctor, package = env_altered_files
    assert find_altered_packages(prefix) == {package: [lib_doctor]}


def test_json_keys_missing(env_ok: tuple[Path, str, str, str], capsys):
    """Test that runs for the case with empty json"""
    prefix, _, _, package = env_ok
    file = prefix / "conda-meta" / f"{package}.json"
    with open(file) as f:
        data = json.load(f)
    del data["paths_data"]
    with open(file, "w") as f:
        json.dump(data, f)

    assert find_altered_packages(prefix) == {}


def test_wrong_path_version(env_ok: tuple[Path, str, str, str]):
    """Test that runs for the case when path_version is not equal to 1"""
    prefix, _, _, package = env_ok
    file = prefix / "conda-meta" / f"{package}.json"
    with open(file) as f:
        data = json.load(f)
        data["paths_data"]["paths_version"] = 2
    with open(file, "w") as f:
        json.dump(data, f)

    assert find_altered_packages(prefix) == {}


def test_json_cannot_be_loaded(env_ok: tuple[Path, str, str, str]):
    """Test that runs for the case when json file is missing"""
    prefix, _, _, package = env_ok
    # passing a None type to json.loads() so that it fails
    package = None
    assert find_altered_packages(prefix) == {}


@pytest.mark.parametrize("verbose", [True, False])
def test_display_health_checks(
    env_ok: tuple[Path, str, str, str], verbose: bool, capsys, monkeypatch: MonkeyPatch
):
    """Test that runs display_health_checks without missing or altered files."""
    prefix, bin_doctor, lib_doctor, package = env_ok
    monkeypatch.setenv("CONDA_PREFIX", str(prefix))
    reset_context()
    display_health_checks(prefix, verbose=verbose)
    captured = capsys.readouterr()
    assert "There are no packages with missing files." in captured.out
    assert "There are no packages with altered files." in captured.out


@pytest.mark.parametrize("verbose", [True, False])
def test_display_health_checks_missing_files(
    env_missing_files: tuple[Path, str, str, str],
    verbose: bool,
    capsys,
    monkeypatch: MonkeyPatch,
):
    """Test that runs display_health_checks with missing files"""
    prefix, bin_doctor, _, package = env_missing_files
    monkeypatch.setenv("CONDA_PREFIX", str(prefix))
    reset_context()
    display_health_checks(prefix, verbose=verbose)
    captured = capsys.readouterr()
    if verbose:
        assert str(bin_doctor) in captured.out
    else:
        assert f"{package}: 1" in captured.out


@pytest.mark.parametrize("verbose", [True, False])
def test_display_health_checks_altered_files(
    env_altered_files: tuple[Path, str, str, str],
    verbose: bool,
    capsys,
    monkeypatch: MonkeyPatch,
):
    """Test that runs display_health_checks with altered files"""
    prefix, _, lib_doctor, package = env_altered_files
    monkeypatch.setenv("CONDA_PREFIX", str(prefix))
    reset_context()
    display_health_checks(prefix, verbose=verbose)
    captured = capsys.readouterr()
    if verbose:
        assert str(lib_doctor) in captured.out
    else:
        assert f"{package}: 1" in captured.out
