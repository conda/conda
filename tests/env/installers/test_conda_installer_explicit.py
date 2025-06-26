# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Tests for the conda installer's handling of explicit environments."""

import pytest

from conda.env.env import Environment
from conda.env.installers.conda import install
from conda.env.specs.requirements import RequirementsSpec
from tests.env import support_file


@pytest.fixture(scope="module")
def support_explicit_file():
    """Path to the explicit environment file in the test support directory"""
    return support_file("explicit.txt")


@pytest.fixture(scope="module")
def explicit_urls():
    """Return a list of explicit URLs for testing."""
    return [
        "@EXPLICIT",
        "https://repo.anaconda.com/pkgs/main/linux-64/python-3.9.0-h2a148a8_4.tar.bz2",
        "https://repo.anaconda.com/pkgs/main/linux-64/conda-4.10.1-py39h06a4308_1.tar.bz2",
    ]


@pytest.fixture(scope="function")
def explicit_env():
    """Create an Environment instance with explicit specs for testing."""
    urls = [
        "@EXPLICIT",
        "https://repo.anaconda.com/pkgs/main/linux-64/python-3.9.0-h2a148a8_4.tar.bz2",
    ]
    return Environment(dependencies=urls)


@pytest.fixture(scope="function")
def regular_env():
    """Create a regular Environment instance for testing."""
    return Environment(dependencies=["python=3.9"])


@pytest.fixture(scope="function")
def mock_explicit(mocker):
    """Mock the explicit function from misc using mocker."""
    # Create a mock with a success return value
    mock_func = mocker.Mock(return_value={"success": True})

    # Patch the function using mocker.patch
    mocker.patch("conda.misc.explicit", mock_func)
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
    explicit_env, regular_env, mock_explicit, mock_solver, tmp_path, mocker
):
    """Test that the installer uses type checking to identify explicit environments."""
    # Create a mock args object
    args = mocker.Mock()

    # Call installer with ExplicitEnvironment using tmp_path as prefix
    install(tmp_path, [], args, explicit_env)

    # Verify explicit() was called for ExplicitEnvironment
    mock_explicit.assert_called_once()

    # Verify _solve was not called for ExplicitEnvironment
    mock_solver.assert_not_called()

    # Reset mocks
    mock_explicit.reset_mock()
    mock_solver.reset_mock()

    # Call installer with regular Environment
    install(tmp_path, [], args, regular_env)

    # Verify _solve was called for regular Environment
    mock_solver.assert_called_once()

    # Verify explicit() was not called for regular Environment
    mock_explicit.assert_not_called()


def test_installer_uses_original_file(
    support_explicit_file, mock_explicit, tmp_path, mocker
):
    """Test that the installer uses the original file when available."""
    # Create spec from a real file
    spec = RequirementsSpec(filename=support_explicit_file)
    env = spec.environment

    # Call installer with tmp_path as prefix
    install(tmp_path, [], mocker.Mock(), env)

    # Get the args passed to explicit()
    args, kwargs = mock_explicit.call_args

    # First arg should be a list of package URLs
    assert isinstance(args[0], list)

    # The file contents should include @EXPLICIT and package URLs
    assert len(args[0]) == 3  # @EXPLICIT marker + 2 packages
    assert args[0][0] == "@EXPLICIT"  # First line should be the marker

    # Verify that the lines from the file are passed to explicit()
    # not the filename itself
    assert not any(arg == support_explicit_file for arg in args[0])
    assert all(isinstance(line, str) for line in args[0])

    # Verify that all lines after the marker are package URLs
    for line in args[0][1:]:
        assert line.startswith("https://"), f"Expected URL but got: {line}"


def test_installer_handles_missing_filename(
    explicit_urls, mock_explicit, tmp_path, mocker
):
    """Test that the installer handles Environment with explicit specs but no filename."""
    # Create Environment with explicit specs but without a filename
    env = Environment(dependencies=explicit_urls)

    # Call installer with tmp_path as prefix
    install(tmp_path, [], mocker.Mock(), env)

    # Verify explicit() was called with the dependencies
    mock_explicit.assert_called_once()
    args, kwargs = mock_explicit.call_args
    assert args[0] == explicit_urls


@pytest.mark.parametrize(
    "explicit_deps",
    [
        # @EXPLICIT at the beginning
        [
            "@EXPLICIT",
            "https://repo.anaconda.com/pkgs/main/linux-64/python-3.9.0-h2a148a8_4.tar.bz2",
            "https://repo.anaconda.com/pkgs/main/linux-64/numpy-1.21.0-py39h2a9ead8_0.tar.bz2",
        ],
        # @EXPLICIT in the middle
        [
            "https://repo.anaconda.com/pkgs/main/linux-64/python-3.9.0-h2a148a8_4.tar.bz2",
            "@EXPLICIT",
            "https://repo.anaconda.com/pkgs/main/linux-64/numpy-1.21.0-py39h2a9ead8_0.tar.bz2",
        ],
        # @EXPLICIT at the end
        [
            "https://repo.anaconda.com/pkgs/main/linux-64/python-3.9.0-h2a148a8_4.tar.bz2",
            "https://repo.anaconda.com/pkgs/main/linux-64/numpy-1.21.0-py39h2a9ead8_0.tar.bz2",
            "@EXPLICIT",
        ],
    ],
    ids=["explicit_at_start", "explicit_in_middle", "explicit_at_end"],
)
def test_explicit_marker_position_with_user_specs(
    explicit_deps: list[str], mock_explicit, tmp_path, monkeypatch
) -> None:
    """Test that @EXPLICIT marker works at any position and user specs are tracked separately."""
    # Arrange
    env = Environment(dependencies=explicit_deps, filename="/path/to/test.txt")
    user_specs = ["numpy>=1.20"]

    # Mock file reading to return the explicit specs
    monkeypatch.setattr(
        "conda.env.installers.conda.yield_lines", lambda *args: explicit_deps
    )

    # Act
    install(tmp_path, user_specs, tmp_path, env)

    # Assert
    mock_explicit.assert_called_once()

    args, kwargs = mock_explicit.call_args

    # Verify user-requested specs are tracked separately
    assert kwargs.get("requested_specs") == user_specs

    # Verify all explicit specs are still passed for installation
    assert "@EXPLICIT" in args[0]
    assert len(args[0]) == 3  # @EXPLICIT + 2 package URLs

    # Verify that the original order is preserved
    assert args[0] == explicit_deps
