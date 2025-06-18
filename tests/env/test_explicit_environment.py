# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Tests for Environment class with explicit functionality."""

import pytest

from conda.env.env import Environment
from conda.env.specs.requirements import RequirementsSpec
from tests.env import support_file


@pytest.fixture(scope="module")
def support_explicit_file():
    """Path to the explicit environment file in the test support directory"""
    return support_file("explicit.txt")


@pytest.fixture(scope="module")
def explicit_urls():
    """Sample URLs for testing explicit environments."""
    return [
        "https://conda.anaconda.org/conda-forge/linux-64/numpy-1.21.5-py39h2a9ead8_0.tar.bz2",
        "https://conda.anaconda.org/conda-forge/linux-64/python-3.9.10-h85951f9_5_cpython.tar.bz2",
    ]


@pytest.fixture(scope="function")
def explicit_env(explicit_urls):
    """Create an Environment instance with explicit specs for testing."""
    return Environment(
        name="test-explicit",
        dependencies=["@EXPLICIT"] + explicit_urls,
        filename="/path/to/explicit-file.txt",
    )


def test_explicit_environment_is_explicit():
    """Test that Environment with @EXPLICIT marker returns True for explicit()."""
    env = Environment(dependencies=["@EXPLICIT", "test"])
    assert env.dependencies.explicit

    regular_env = Environment()
    assert not regular_env.dependencies.explicit


def test_explicit_environment_initialization(explicit_urls):
    """Test Environment initialization with explicit parameters."""
    explicit_deps = ["@EXPLICIT"] + explicit_urls
    env = Environment(
        name="test-env",
        dependencies=explicit_deps,
        filename="/path/to/test.txt",
    )

    # Check standard Environment properties
    assert env.name == "test-env"
    assert len(env.dependencies.raw) == 3  # @EXPLICIT + 2 URLs

    # Check explicit-specific properties
    assert env.dependencies.raw == explicit_deps
    assert env.filename == "/path/to/test.txt"
    assert env.dependencies.explicit


def test_explicit_marker_in_middle(explicit_urls):
    """Test that @EXPLICIT marker works when it's in the middle of dependencies."""
    # Test with @EXPLICIT in the middle
    deps_with_middle_explicit = explicit_urls[:1] + ["@EXPLICIT"] + explicit_urls[1:]
    env_middle = Environment(
        name="test-explicit-middle",
        dependencies=deps_with_middle_explicit,
        filename="/path/to/explicit-file.txt",
    )
    assert env_middle.dependencies.explicit
    assert "@EXPLICIT" in env_middle.dependencies.raw


def test_explicit_marker_at_end(explicit_urls):
    """Test that @EXPLICIT marker works when it's at the end of dependencies."""
    # Test with @EXPLICIT at the end
    deps_with_end_explicit = explicit_urls + ["@EXPLICIT"]
    env_end = Environment(
        name="test-explicit-end",
        dependencies=deps_with_end_explicit,
        filename="/path/to/explicit-file.txt",
    )
    assert env_end.dependencies.explicit
    assert "@EXPLICIT" in env_end.dependencies.raw


def test_requirements_spec_returns_explicit_environment(support_explicit_file):
    """Test that RequirementsSpec returns an Environment instance with explicit specs."""
    spec = RequirementsSpec(filename=support_explicit_file)
    env = spec.environment

    # Verify it's the right type
    assert isinstance(env, Environment)
    assert env.dependencies.explicit

    # Check expected attributes
    assert env.filename == support_explicit_file
    assert len(env.dependencies.raw) == 3  # @EXPLICIT + 2 package URLs


def test_explicit_environment_for_cep23_compliance(explicit_env):
    """Test that Environment with explicit specs follows CEP-23 by detecting explicit format in dependencies."""
    # The environment should have dependencies with @EXPLICIT marker
    assert explicit_env.dependencies is not None
    assert "@EXPLICIT" in explicit_env.dependencies.raw

    # Filename should be stored
    assert explicit_env.filename is not None

    # Should be identified as explicit
    assert explicit_env.dependencies.explicit
