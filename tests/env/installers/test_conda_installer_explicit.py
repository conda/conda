# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Test conda explicit installer functionality."""

import pytest

from conda.env.env import Environment
from conda.env.installers.conda import install


@pytest.fixture
def explicit_urls():
    """Sample explicit package URLs for testing."""
    return [
        "@EXPLICIT",
        "https://repo.anaconda.com/pkgs/main/linux-64/python-3.9.0-h2a148a8_4.tar.bz2",
    ]


@pytest.fixture
def explicit_env(explicit_urls):
    """Create an Environment instance for testing."""
    return Environment(dependencies=explicit_urls)


@pytest.fixture
def mock_args():
    """Mock args object for testing."""

    class MockArgs:
        prune = False

    return MockArgs()


def test_installer_handles_explicit_environment(explicit_env, mock_args):
    """Test that the installer correctly identifies and handles explicit environments."""
    # Should detect as explicit environment
    assert explicit_env.dependencies.explicit is True


def test_installer_uses_explicit_function(
    monkeypatch, explicit_env, mock_args, tmp_path
):
    """Test that installer calls explicit() function for explicit environments."""
    # Track calls to explicit function
    explicit_calls = []

    def mock_explicit(*args, **kwargs):
        explicit_calls.append((args, kwargs))
        return {"success": True}

    # Mock the explicit function
    monkeypatch.setattr("conda.misc.explicit", mock_explicit)

    # Call installer with Environment
    install(str(tmp_path), [], mock_args, explicit_env)

    # Verify explicit() was called
    assert len(explicit_calls) == 1

    # Check the arguments passed to explicit()
    call_args, call_kwargs = explicit_calls[0]
    explicit_specs = call_args[0]  # First positional argument
    prefix = call_args[1]  # Second positional argument

    # Should include @EXPLICIT marker
    assert "@EXPLICIT" in explicit_specs
    assert prefix == str(tmp_path)


def test_installer_preserves_original_file(monkeypatch, tmp_path, mock_args):
    """Test installer preserves the original explicit file."""
    # Create a temporary explicit file
    explicit_file = tmp_path / "test.txt"
    explicit_file.write_text("@EXPLICIT\nhttps://example.com/package.tar.bz2\n")

    # Create environment with filename
    env = Environment(
        dependencies=["@EXPLICIT", "https://example.com/package.tar.bz2"],
        filename=str(explicit_file),
    )

    # Track calls to explicit function
    explicit_calls = []

    def mock_explicit(*args, **kwargs):
        explicit_calls.append((args, kwargs))
        return {"success": True}

    # Mock the explicit function
    monkeypatch.setattr("conda.misc.explicit", mock_explicit)

    # Call installer
    install(str(tmp_path), [], mock_args, env)

    # Verify explicit() was called
    assert len(explicit_calls) == 1


def test_installer_handles_missing_filename(explicit_urls, mock_args):
    """Test that the installer handles Environment with no filename."""
    # Create Environment without a filename
    env = Environment(dependencies=explicit_urls)

    # Should still detect as explicit
    assert env.dependencies.explicit is True


def test_installer_bypasses_solver_for_explicit(
    monkeypatch, explicit_env, mock_args, tmp_path
):
    """Test that installer bypasses solver for explicit environments."""
    # Track calls to functions
    solve_calls = []
    explicit_calls = []

    def mock_solve(*args, **kwargs):
        solve_calls.append((args, kwargs))
        return None

    def mock_explicit(*args, **kwargs):
        explicit_calls.append((args, kwargs))
        return {"success": True}

    # Mock both functions
    monkeypatch.setattr("conda.env.installers.conda._solve", mock_solve)
    monkeypatch.setattr("conda.misc.explicit", mock_explicit)

    # Call installer with explicit environment
    install(str(tmp_path), [], mock_args, explicit_env)

    # Solver should not be called for explicit environments
    assert len(solve_calls) == 0

    # But explicit() should be called
    assert len(explicit_calls) == 1
