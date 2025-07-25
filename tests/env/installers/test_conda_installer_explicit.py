# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Test conda explicit installer functionality."""

import pytest

from conda.env.installers.conda import install
from conda.env.specs.explicit import ExplicitSpec
from conda.models.environment import Environment
from conda.models.match_spec import MatchSpec
from conda.models.records import PackageRecord
from tests.env import support_file


@pytest.fixture(scope="module")
def support_explicit_file():
    """Path to the explicit environment file in the test support directory"""
    return support_file("explicit.txt")


@pytest.fixture(scope="function")
def explicit_env():
    """Create an Environment instance with explicit specs for testing."""
    test_record = PackageRecord(
        name="python",
        version="3.9.0",
        build="h2a148a8",
        channel="main",
        subdir="linux-64",
        build_number=4,
        url="https://repo.anaconda.com/pkgs/main/linux-64/python-3.9.0-h2a148a8_4.tar.bz2",
    )
    return Environment(
        prefix="/path/to/env",
        platform="linux-64",
        explicit_packages=[test_record],
    )


@pytest.fixture(scope="function")
def regular_env():
    """Create a regular Environment instance for testing."""
    return Environment(
        prefix="/path/to/env",
        platform="linux-64",
        requested_packages=[MatchSpec("python=3.9")],
    )


@pytest.fixture(scope="function")
def mock_install_explicit_packages(mocker):
    """Mock the install_explicit_packages function from misc using mocker."""
    # Create a mock with a success return value
    mock_func = mocker.Mock(return_value={"success": True})

    # Patch the function using mocker.patch
    mocker.patch("conda.misc.install_explicit_packages", mock_func)
    return mock_func


@pytest.fixture(scope="function")
def mock_solver(mocker):
    """Mock the _solve function using mocker to verify it's not called for explicit environments."""
    # Create a chain of mocks for the solver process
    solver_mock = mocker.Mock()

    # Create a transaction mock with the needed methods
    transaction_mock = mocker.Mock()
    transaction_mock.nothing_to_do = False

    # Create a mock for the action groups return value
    action_groups_mock = mocker.Mock()
    # When _make_legacy_action_groups() is called, return a list with one item
    transaction_mock._make_legacy_action_groups.return_value = [action_groups_mock]

    # Set up the transaction to be downloaded and executed without errors
    transaction_mock.download_and_extract.return_value = None
    transaction_mock.execute.return_value = None

    # Make the solver return our transaction
    solver_mock.solve_for_transaction.return_value = transaction_mock

    # Set up the _solve function to return our solver mock
    mock_solve = mocker.Mock(return_value=solver_mock)
    mocker.patch("conda.env.installers.conda._solve", mock_solve)
    return mock_solve


def test_installer_type_checking_for_explicit(
    explicit_env,
    regular_env,
    mock_install_explicit_packages,
    mock_solver,
    tmp_path,
    mocker,
):
    """Test that installer calls explicit() function for explicit environments."""
    # Call installer with explicit environment
    install(str(tmp_path), [], mocker.Mock(), explicit_env)

    # Verify explicit() was called for ExplicitEnvironment
    mock_install_explicit_packages.assert_called_once()

    # Reset mocks
    mock_install_explicit_packages.reset_mock()
    mock_solver.reset_mock()

    # Call installer with regular environment
    install(str(tmp_path), [], mocker.Mock(), regular_env)

    # Verify _solve was called for regular Environment
    mock_solver.assert_called_once()

    # Verify explicit() was not called for regular Environment
    mock_install_explicit_packages.assert_not_called()


def test_installer_installs_explicit(
    support_explicit_file, mock_install_explicit_packages, tmp_path, mocker
):
    """Test that the installer installs explicit packages"""
    # Create spec from a real file
    spec = ExplicitSpec(filename=support_explicit_file)
    env = spec.env

    # Call installer with tmp_path as prefix
    install(tmp_path, [], mocker.Mock(), env)

    # Get the args passed to explicit()
    _, kwargs = mock_install_explicit_packages.call_args

    package_cache_records_kwarg = kwargs.get("package_cache_records")
    # Should be a list of package cache records
    for kwarg in package_cache_records_kwarg:
        assert isinstance(kwarg, PackageRecord)

    assert len(package_cache_records_kwarg) == 2  # 2 packages


def test_explicit_with_user_specs(
    explicit_env, mock_install_explicit_packages, tmp_path, mocker
) -> None:
    """Test that user specs are tracked separately."""
    user_specs = ["numpy>=1.20"]

    # Act
    install(tmp_path, user_specs, mocker.Mock(), explicit_env)

    # Assert
    mock_install_explicit_packages.assert_called_once()

    _, kwargs = mock_install_explicit_packages.call_args

    # Verify all explicit specs are still passed for installation
    assert len(kwargs.get("package_cache_records")) == 1  # 1 package URL
