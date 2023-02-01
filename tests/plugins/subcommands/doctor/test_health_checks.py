# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from pathlib import Path
from conda.plugins.subcommands.doctor import health_checks
import json
import pytest

BIN_TEST_EXE = "bin/test-exe"
LIB_TEST_PACKAGE = "lib/test-package.py"
TEST_PACKAGE_JSON = "test-package.json"

PACKAGE_JSON = {"files": [BIN_TEST_EXE, LIB_TEST_PACKAGE]}

PACKAGE_JSON_WITH_MISSING_FILES = {"files": [BIN_TEST_EXE, LIB_TEST_PACKAGE, "missing.py"]}


@pytest.fixture()
def conda_mock_dir(tmpdir):
    """Fixture that returns a testing environment with no missing files"""
    tmpdir.mkdir("bin")
    tmpdir.mkdir("lib")
    conda_meta_dir = tmpdir.mkdir("conda-meta")

    with Path(conda_meta_dir).joinpath(TEST_PACKAGE_JSON).open("w") as fp:
        json.dump(PACKAGE_JSON, fp)

    Path(tmpdir).joinpath(BIN_TEST_EXE).touch()
    Path(tmpdir).joinpath(LIB_TEST_PACKAGE).touch()

    return tmpdir


@pytest.fixture()
def conda_mock_dir_missing_files(conda_mock_dir):
    """Fixture that returns a testing environment with missing files"""
    Path(conda_mock_dir).joinpath(BIN_TEST_EXE).unlink()

    return conda_mock_dir


def test_find_packages_with_no_missing_files(conda_mock_dir):
    """Test that runs for the case with no missing files"""
    result = health_checks.find_packages_with_missing_files(conda_mock_dir)
    assert result == {}


def test_find_packages_with_missing_files(conda_mock_dir_missing_files):
    result = health_checks.find_packages_with_missing_files(conda_mock_dir_missing_files)
    TEST_PACKAGE_JSON = "test-package"
    assert result == {TEST_PACKAGE_JSON: [BIN_TEST_EXE]}


def test_get_number_of_missing_files(conda_mock_dir_missing_files):
    result = health_checks.get_number_of_missing_files(conda_mock_dir_missing_files)
    TEST_PACKAGE_JSON = "test-package"
    assert result == {TEST_PACKAGE_JSON: 1}


def test_get_number_of_missing_files_when_no_missing_files(conda_mock_dir):
    result = health_checks.get_number_of_missing_files(conda_mock_dir)
    assert result == {}


def test_get_names_of_missing_files(conda_mock_dir_missing_files):
    result = health_checks.get_names_of_missing_files(conda_mock_dir_missing_files)
    TEST_PACKAGE_JSON = "test-package"
    assert result == {TEST_PACKAGE_JSON: [BIN_TEST_EXE]}


def test_get_names_of_missing_files_when_no_missing_files(conda_mock_dir):
    result = health_checks.get_names_of_missing_files(conda_mock_dir)
    TEST_PACKAGE_JSON = "test-package"
    assert result == {}
