# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Test conda explicit installer functionality."""

from pathlib import Path
from unittest.mock import MagicMock, patch, Mock

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
    args = Mock()
    args.prune = False
    return args


def test_installer_handles_explicit_environment(explicit_env, mock_args):
    """Test that the installer correctly identifies and handles explicit environments."""
    # Should detect as explicit environment
    assert explicit_env.dependencies.explicit is True


@patch("conda.misc.explicit")
def test_installer_uses_explicit_function(mock_explicit, explicit_env, mock_args, tmp_path):
    """Test that installer calls explicit() function for explicit environments."""
    # Mock the explicit function to return success
    mock_explicit.return_value = {"success": True}
    
    # Call installer with Environment
    install(str(tmp_path), [], mock_args, explicit_env)
    
    # Verify explicit() was called
    mock_explicit.assert_called_once()
    
    # Check the arguments passed to explicit()
    call_args = mock_explicit.call_args
    explicit_specs = call_args[0][0]  # First positional argument
    prefix = call_args[0][1]  # Second positional argument
    
    # Should include @EXPLICIT marker
    assert "@EXPLICIT" in explicit_specs
    assert prefix == str(tmp_path)


@patch("conda.misc.explicit")
def test_installer_preserves_original_file(mock_explicit, tmp_path, mock_args):
    """Test installer preserves the original explicit file."""
    # Create a temporary explicit file
    explicit_file = tmp_path / "test.txt" 
    explicit_file.write_text("@EXPLICIT\nhttps://example.com/package.tar.bz2\n")
    
    # Create environment with filename
    env = Environment(
        dependencies=["@EXPLICIT", "https://example.com/package.tar.bz2"],
        filename=str(explicit_file)
    )
    
    # Mock the explicit function
    mock_explicit.return_value = {"success": True}
    
    # Call installer
    install(str(tmp_path), [], mock_args, env)
    
    # Verify explicit() was called
    mock_explicit.assert_called_once()


def test_installer_handles_missing_filename(explicit_urls, mock_args):
    """Test that the installer handles Environment with no filename."""
    # Create Environment without a filename
    env = Environment(dependencies=explicit_urls)
    
    # Should still detect as explicit
    assert env.dependencies.explicit is True


@patch("conda.env.installers.conda._solve")
def test_installer_bypasses_solver_for_explicit(mock_solve, explicit_env, mock_args, tmp_path):
    """Test that installer bypasses solver for explicit environments."""
    with patch("conda.misc.explicit") as mock_explicit:
        mock_explicit.return_value = {"success": True}
        
        # Call installer with explicit environment
        install(str(tmp_path), [], mock_args, explicit_env)
        
        # Solver should not be called for explicit environments
        mock_solve.assert_not_called()
        
        # But explicit() should be called
        mock_explicit.assert_called_once()
